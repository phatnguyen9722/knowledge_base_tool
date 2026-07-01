# Knowledge Base Tool – Requirements
> Option B: FastAPI + pystray + PyInstaller  
> Mục tiêu: app chạy local, mở trong browser, có system tray icon, không cần terminal

---

## Stack

| Layer | Technology | Ghi chú |
|-------|-----------|---------|
| Storage | Markdown files + SQLite FTS5 | posts/*.md + .kb/search.db |
| Backend | FastAPI + Uvicorn | REST API + Jinja2 templates |
| Frontend | Jinja2 + marked.js | render trong browser |
| Desktop | pystray + Pillow | system tray icon |
| CLI | Typer | kb new / list / search / export |
| Build | PyInstaller | đóng gói .exe / .app |

---

## Cấu trúc thư mục

```
knowledge-base/
├── app/
│   ├── main.py              # FastAPI app entry
│   ├── models.py            # Pydantic Post schema
│   ├── post_manager.py      # CRUD + slugify
│   ├── search.py            # SQLite FTS5 engine
│   ├── tag_manager.py       # tag index + suggest
│   └── exporter.py          # HTML / JSON / CSV export
├── templates/               # Jinja2 HTML templates
│   ├── base.html
│   ├── list.html
│   ├── detail.html
│   └── editor.html
├── static/
│   ├── style.css
│   ├── app.js               # search debounce, marked.js glue
│   └── icon.png             # 64x64 tray icon
├── posts/                   # *.md files (user data)
├── attachments/             # images, file đính kèm
├── .kb/
│   └── search.db            # SQLite FTS5 (auto-generated)
├── config.yaml              # port, data_dir, theme
├── launcher.py              # pystray entry point
├── cli.py                   # Typer CLI
└── requirements.txt
```

---

## Python dependencies

```
# requirements.txt
fastapi
uvicorn[standard]
jinja2
python-frontmatter
pydantic>=2
mistune>=3
python-slugify
pystray
pillow
typer
pyyaml
pyinstaller
```

Cài tất cả:
```bash
pip install -r requirements.txt
```

---

## Frontmatter schema (mỗi file .md)

```yaml
---
title: "Docker Compose Cheatsheet"   # required – str
created: 2024-01-15                  # required – YYYY-MM-DD
updated: 2024-06-20                  # required – YYYY-MM-DD
tags: [docker, devops, commands]     # required – list[str]
category: DevOps                     # required – str
status: published                    # required – published | draft | archived
pinned: false                        # optional – bool, default false
summary: "Tóm tắt ngắn hiện ở card" # optional – str
---

Nội dung markdown bắt đầu từ đây...
```

---

## Pydantic model (`app/models.py`)

```python
from pydantic import BaseModel, field_validator
from datetime import date
from typing import Literal
from enum import Enum

class PostStatus(str, Enum):
    published = "published"
    draft = "draft"
    archived = "archived"

class Post(BaseModel):
    slug: str
    title: str
    created: date
    updated: date
    tags: list[str]
    category: str
    status: PostStatus = PostStatus.published
    pinned: bool = False
    summary: str = ""
    content: str = ""            # raw markdown body

    @field_validator("tags", mode="before")
    @classmethod
    def normalize_tags(cls, v):
        return [t.lower().strip() for t in v] if v else []
```

---

## PostManager (`app/post_manager.py`)

```python
from pathlib import Path
import frontmatter
from slugify import slugify
from .models import Post
from .search import SearchEngine

class PostManager:
    def __init__(self, posts_dir: Path, db_path: Path):
        self.posts_dir = posts_dir
        self.search = SearchEngine(db_path)

    def _path(self, slug: str) -> Path:
        return self.posts_dir / f"{slug}.md"

    def create(self, data: dict) -> Post:
        slug = slugify(data["title"], allow_unicode=True)
        post = Post(slug=slug, **data)
        self._write(post)
        self.search.index(post)
        return post

    def read(self, slug: str) -> Post | None:
        path = self._path(slug)
        if not path.exists():
            return None
        fm = frontmatter.load(str(path))
        return Post(slug=slug, content=fm.content, **fm.metadata)

    def update(self, slug: str, data: dict) -> Post | None:
        post = self.read(slug)
        if not post:
            return None
        updated = post.model_copy(update=data)
        self._write(updated)
        self.search.index(updated)
        return updated

    def delete(self, slug: str) -> bool:
        path = self._path(slug)
        if not path.exists():
            return False
        path.unlink()
        self.search.remove(slug)
        return True

    def list(self, status: str | None = None) -> list[Post]:
        posts = []
        for f in sorted(self.posts_dir.glob("*.md"), reverse=True):
            post = self.read(f.stem)
            if post and (status is None or post.status == status):
                posts.append(post)
        posts.sort(key=lambda p: (not p.pinned, p.updated), reverse=False)
        return posts

    def _write(self, post: Post):
        meta = post.model_dump(exclude={"content", "slug"})
        fm = frontmatter.Post(post.content, **meta)
        self.posts_dir.mkdir(parents=True, exist_ok=True)
        frontmatter.dump(fm, str(self._path(post.slug)))
```

---

## SearchEngine (`app/search.py`)

```python
import sqlite3
from pathlib import Path
from .models import Post

class SearchEngine:
    def __init__(self, db_path: Path):
        db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(str(db_path), check_same_thread=False)
        self._init()

    def _init(self):
        self.conn.execute("""
            CREATE VIRTUAL TABLE IF NOT EXISTS posts_fts
            USING fts5(slug UNINDEXED, title, content, tags, category)
        """)
        self.conn.commit()

    def index(self, post: Post):
        self.conn.execute(
            "DELETE FROM posts_fts WHERE slug = ?", (post.slug,)
        )
        self.conn.execute(
            "INSERT INTO posts_fts VALUES (?, ?, ?, ?, ?)",
            (post.slug, post.title, post.content,
             " ".join(post.tags), post.category)
        )
        self.conn.commit()

    def remove(self, slug: str):
        self.conn.execute("DELETE FROM posts_fts WHERE slug = ?", (slug,))
        self.conn.commit()

    def search(self, query: str, tag: str | None = None,
               category: str | None = None) -> list[str]:
        """Return list of matching slugs, ranked by relevance."""
        base = "SELECT slug FROM posts_fts WHERE posts_fts MATCH ?"
        params = [query]
        if tag:
            base += " AND tags LIKE ?"
            params.append(f"%{tag}%")
        if category:
            base += " AND category = ?"
            params.append(category)
        base += " ORDER BY rank"
        rows = self.conn.execute(base, params).fetchall()
        return [r[0] for r in rows]

    def rebuild(self, posts: list[Post]):
        self.conn.execute("DELETE FROM posts_fts")
        for post in posts:
            self.conn.execute(
                "INSERT INTO posts_fts VALUES (?, ?, ?, ?, ?)",
                (post.slug, post.title, post.content,
                 " ".join(post.tags), post.category)
            )
        self.conn.commit()
```

---

## FastAPI app (`app/main.py`)

```python
from fastapi import FastAPI, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pathlib import Path
import sys

# Resolve paths – works both in dev and PyInstaller bundle
if getattr(sys, "frozen", False):
    BASE = Path(sys._MEIPASS)
else:
    BASE = Path(__file__).parent.parent

POSTS_DIR = BASE / "posts"
DB_PATH   = BASE / ".kb" / "search.db"
TEMPLATES = BASE / "templates"
STATIC    = BASE / "static"

from .post_manager import PostManager
from .tag_manager import TagManager

app = FastAPI()
app.mount("/static", StaticFiles(directory=str(STATIC)), name="static")
templates = Jinja2Templates(directory=str(TEMPLATES))

pm = PostManager(POSTS_DIR, DB_PATH)
tm = TagManager(POSTS_DIR)

@app.get("/", response_class=HTMLResponse)
async def list_posts(request: Request, tag: str = "", q: str = "", status: str = "published"):
    if q:
        slugs = pm.search.search(q, tag=tag or None)
        posts = [pm.read(s) for s in slugs if pm.read(s)]
    else:
        posts = pm.list(status=status or None)
        if tag:
            posts = [p for p in posts if tag in p.tags]
    return templates.TemplateResponse("list.html", {
        "request": request, "posts": posts,
        "tags": tm.all_tags(), "q": q, "active_tag": tag
    })

@app.get("/posts/{slug}", response_class=HTMLResponse)
async def detail(request: Request, slug: str):
    post = pm.read(slug)
    if not post:
        raise HTTPException(404)
    return templates.TemplateResponse("detail.html", {"request": request, "post": post})

@app.get("/new", response_class=HTMLResponse)
async def new_form(request: Request):
    return templates.TemplateResponse("editor.html", {"request": request, "post": None})

@app.post("/new")
async def create_post(title: str = Form(...), content: str = Form(...),
                      tags: str = Form(""), category: str = Form("General"),
                      status: str = Form("published")):
    from datetime import date
    post = pm.create({
        "title": title, "content": content,
        "tags": [t.strip() for t in tags.split(",") if t.strip()],
        "category": category, "status": status,
        "created": date.today(), "updated": date.today(),
    })
    tm.rebuild()
    return RedirectResponse(f"/posts/{post.slug}", status_code=303)

@app.get("/edit/{slug}", response_class=HTMLResponse)
async def edit_form(request: Request, slug: str):
    post = pm.read(slug)
    if not post:
        raise HTTPException(404)
    return templates.TemplateResponse("editor.html", {"request": request, "post": post})

@app.post("/edit/{slug}")
async def update_post(slug: str, title: str = Form(...), content: str = Form(...),
                      tags: str = Form(""), category: str = Form("General"),
                      status: str = Form("published")):
    from datetime import date
    pm.update(slug, {
        "title": title, "content": content,
        "tags": [t.strip() for t in tags.split(",") if t.strip()],
        "category": category, "status": status, "updated": date.today(),
    })
    tm.rebuild()
    return RedirectResponse(f"/posts/{slug}", status_code=303)

@app.delete("/posts/{slug}")
async def delete_post(slug: str):
    if not pm.delete(slug):
        raise HTTPException(404)
    tm.rebuild()
    return {"ok": True}

@app.get("/api/search")
async def api_search(q: str = "", tag: str = "", category: str = ""):
    slugs = pm.search.search(q, tag=tag or None, category=category or None)
    posts = [pm.read(s) for s in slugs if pm.read(s)]
    return [p.model_dump(exclude={"content"}) for p in posts]
```

---

## TagManager (`app/tag_manager.py`)

```python
import json
from pathlib import Path
from collections import Counter
import frontmatter as fm_lib

class TagManager:
    def __init__(self, posts_dir: Path):
        self.posts_dir = posts_dir
        self.index_path = posts_dir.parent / "tags" / "index.json"

    def all_tags(self) -> dict[str, int]:
        """Return {tag: count} sorted by count desc."""
        counter: Counter = Counter()
        for f in self.posts_dir.glob("*.md"):
            try:
                meta = fm_lib.load(str(f)).metadata
                for t in meta.get("tags", []):
                    counter[t.lower().strip()] += 1
            except Exception:
                pass
        return dict(counter.most_common())

    def rebuild(self):
        tags = self.all_tags()
        self.index_path.parent.mkdir(parents=True, exist_ok=True)
        self.index_path.write_text(json.dumps(tags, ensure_ascii=False, indent=2))
```

---

## Launcher (`launcher.py`)

```python
import threading
import webbrowser
import time
import sys
from pathlib import Path
import uvicorn
import pystray
from PIL import Image

PORT = 5000
URL  = f"http://localhost:{PORT}"

def run_server():
    from app.main import app
    uvicorn.run(app, host="127.0.0.1", port=PORT, log_level="error")

def open_browser(icon, item):
    webbrowser.open(URL)

def quit_app(icon, item):
    icon.stop()
    sys.exit(0)

if __name__ == "__main__":
    # Resolve icon path (works in dev + PyInstaller bundle)
    if getattr(sys, "frozen", False):
        base = Path(sys._MEIPASS)
    else:
        base = Path(__file__).parent

    # Start FastAPI in background thread
    t = threading.Thread(target=run_server, daemon=True)
    t.start()
    time.sleep(1.5)           # wait for server to be ready
    webbrowser.open(URL)      # open browser on first launch

    # System tray icon
    icon_path = base / "static" / "icon.png"
    img = Image.open(str(icon_path))
    menu = pystray.Menu(
        pystray.MenuItem("Open Knowledge Base", open_browser, default=True),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("Quit", quit_app),
    )
    icon = pystray.Icon("KnowledgeBase", img, "KB Tool", menu)
    icon.run()    # blocking – keeps app alive
```

---

## CLI (`cli.py`)

```python
import typer
from pathlib import Path
from datetime import date

app = typer.Typer(help="Knowledge Base CLI")

POSTS_DIR = Path("posts")
DB_PATH   = Path(".kb/search.db")

def _pm():
    from app.post_manager import PostManager
    return PostManager(POSTS_DIR, DB_PATH)

@app.command()
def new(title: str = typer.Argument(..., help="Tiêu đề bài viết"),
        category: str = typer.Option("General", "--cat"),
        tags: str = typer.Option("", "--tags", help="Comma-separated")):
    pm = _pm()
    post = pm.create({
        "title": title,
        "tags": [t.strip() for t in tags.split(",") if t.strip()],
        "category": category,
        "status": "draft",
        "created": date.today(),
        "updated": date.today(),
    })
    typer.echo(f"Created: posts/{post.slug}.md")

@app.command()
def list(status: str = typer.Option("published", "--status")):
    pm = _pm()
    for p in pm.list(status=status):
        pin = "📌 " if p.pinned else "   "
        typer.echo(f"{pin}[{p.status}] {p.slug}  –  {p.title}")

@app.command()
def search(query: str, tag: str = "", category: str = ""):
    pm = _pm()
    slugs = pm.search.search(query, tag=tag or None, category=category or None)
    for s in slugs:
        post = pm.read(s)
        if post:
            typer.echo(f"{post.slug}  –  {post.title}")

@app.command()
def serve(port: int = 5000):
    import uvicorn
    from app.main import app as fastapi_app
    uvicorn.run(fastapi_app, host="127.0.0.1", port=port, reload=True)

@app.command()
def build_index():
    from app.tag_manager import TagManager
    tm = TagManager(POSTS_DIR)
    tm.rebuild()
    typer.echo("Tag index rebuilt.")

if __name__ == "__main__":
    app()
```

---

## Build ra file thực thi

```bash
# macOS / Linux
pyinstaller --onefile --noconsole \
    --add-data "templates:templates" \
    --add-data "static:static" \
    --add-data "posts:posts" \
    --name kb-tool \
    launcher.py

# Windows
pyinstaller --onefile --noconsole ^
    --add-data "templates;templates" ^
    --add-data "static;static" ^
    --add-data "posts;posts" ^
    --name kb-tool ^
    launcher.py
```

Output: `dist/kb-tool` (macOS/Linux) hoặc `dist/kb-tool.exe` (Windows)

> **Lưu ý:** `posts/` nằm ngoài bundle. Dùng `config.yaml` để trỏ đến thư mục data nếu cần đặt ở chỗ khác.

---

## Plugin hooks (mở rộng sau)

```python
# app/hooks.py – đăng ký handler cho các sự kiện
_handlers: dict[str, list] = {
    "on_post_created": [],
    "on_post_updated": [],
    "on_post_deleted": [],
}

def on(event: str):
    """Decorator: @on('on_post_created')"""
    def decorator(fn):
        _handlers[event].append(fn)
        return fn
    return decorator

def emit(event: str, payload):
    for fn in _handlers.get(event, []):
        fn(payload)

# Dùng trong post_manager.py:
# from .hooks import emit
# emit("on_post_created", post)
```

---

## Execution plan

| Phase | Nội dung | Thời gian | Deliverable |
|-------|---------|-----------|-------------|
| 1 | Project scaffold + data model | ~3 ngày | Post schema, parser, unit tests |
| 2 | PostManager + Search core | ~4 ngày | CRUD, FTS5, TagManager |
| 3 | API + UI cơ bản | ~5 ngày | **App chạy được trong browser** ✓ |
| 4 | Search UI + Tag browser | ~3 ngày | Full filter, keyboard shortcuts |
| 5 | Launcher + CLI + Build | ~4 ngày | File .exe / .app standalone |

**Milestone:** Sau Phase 3 app đã dùng được. Phase 4–5 là polish và đóng gói.

---

## Checklist từng phase

### Phase 1 – Scaffold & data model
- [ ] Khởi tạo cấu trúc thư mục (posts/ attachments/ tags/ .kb/ static/ templates/)
- [ ] `app/models.py` – Pydantic Post schema với validator
- [ ] `app/__init__.py`, `config.yaml` skeleton
- [ ] Frontmatter parser + validation (python-frontmatter + Pydantic)
- [ ] Unit tests: valid post / missing field / wrong type / UTF-8 tiếng Việt
- [ ] `.gitignore`: `.kb/ __pycache__ dist/ build/ *.spec *.pyc`

### Phase 2 – PostManager & Search core
- [ ] `app/post_manager.py` – create / read / update / delete / list / slugify
- [ ] `app/search.py` – SQLite FTS5, auto-index khi save, highlight snippet
- [ ] `app/tag_manager.py` – build index.json, all_tags(), rebuild()
- [ ] Integration tests: CRUD round-trip, search recall, UTF-8

### Phase 3 – API & UI cơ bản
- [ ] `app/main.py` – FastAPI routes: GET/POST /posts, /search, /new, /edit/{slug}, DELETE
- [ ] `templates/base.html` – layout chung, sidebar tags
- [ ] `templates/list.html` – blog-style feed, pagination, pinned lên đầu
- [ ] `templates/detail.html` – render markdown, metadata header, back link
- [ ] `templates/editor.html` – 2-panel: raw markdown | live preview (marked.js)
- [ ] `static/style.css` + `static/app.js`

### Phase 4 – Search UI & Tag browser
- [ ] Realtime search bar – debounce 200ms, highlight matches
- [ ] Tag cloud + multi-tag filter (AND logic)
- [ ] Status / category dropdown chips, URL-encoded state
- [ ] Keyboard shortcuts: `/` focus search, `n` new, `e` edit, `?` help

### Phase 5 – Launcher, CLI & Build
- [ ] `launcher.py` – pystray + webbrowser + uvicorn thread
- [ ] `static/icon.png` – 64×64 tray icon (tạo bằng Pillow hoặc file sẵn)
- [ ] `cli.py` – Typer: new / list / search / serve / build-index
- [ ] `app/exporter.py` – export HTML static site ra dist/
- [ ] PyInstaller build script (macOS + Windows)
- [ ] `app/hooks.py` – plugin event system
- [ ] Test bundle trên máy không có Python
