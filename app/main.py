"""FastAPI application – routes, templates, and markdown rendering.

Paths are resolved so the app works both in development and inside a
PyInstaller bundle (Phase 5). Configuration is read from `config.yaml`.
"""

from __future__ import annotations

import hashlib
import mimetypes
from datetime import date
from math import ceil
from pathlib import Path
from urllib.parse import urlencode

import mistune
from fastapi import FastAPI, File, Form, HTTPException, Query, Request, UploadFile
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from .api_docs import ApiDocsManager
from .bookmarks import BookmarksManager
from .books import BookManager
from .config import load_settings
from .dictionary_db import DictionaryDB
from pydantic import BaseModel
from .emails import EmailManager
from .markdown import render_with_toc
from .music import MusicManager
from .notes import NOTE_THEMES, NoteManager
from .post_manager import PostManager
from .tag_manager import TagManager
from .tasks import TaskManager
from .toeic import ToeicManager, parse_listening

# --------------------------------------------------------------------------- #
# Settings (paths resolved for dev + PyInstaller bundle)
# --------------------------------------------------------------------------- #
_settings = load_settings()
dict_db = DictionaryDB(str(_settings.dict_db_path))
POSTS_DIR = _settings.posts_dir
IMG_DIR = _settings.img_dir
TOEIC_DIR = _settings.toeic_dir
BOOKS_DIR = _settings.books_dir
MUSIC_DIR = _settings.music_dir
NOTES_DIR = _settings.notes_dir
API_DOCS_DIR = _settings.api_docs_dir
BOOKMARKS_DIR = _settings.bookmarks_dir
TASKS_DIR = _settings.tasks_dir
EMAILS_DIR = _settings.emails_dir
DB_PATH = _settings.db_path
TEMPLATES = _settings.templates
STATIC = _settings.static
PAGE_SIZE = _settings.page_size
THEME = _settings.theme

# Image uploads (pasted into the editor) are stored here and served at /img.
IMG_DIR.mkdir(parents=True, exist_ok=True)
ALLOWED_IMAGE_TYPES = {
    "image/png": ".png",
    "image/jpeg": ".jpg",
    "image/gif": ".gif",
    "image/webp": ".webp",
    "image/svg+xml": ".svg",
    "image/bmp": ".bmp",
}
MAX_IMAGE_BYTES = 10 * 1024 * 1024  # 10 MB

# Background images stored in img/background/
BG_DIR = IMG_DIR / "background"
BG_DIR.mkdir(parents=True, exist_ok=True)

FONTS_DIR = _settings.posts_dir.parent / "fonts"
FONTS_DIR.mkdir(parents=True, exist_ok=True)

# Music uploads are stored here and served at /music.
MUSIC_DIR.mkdir(parents=True, exist_ok=True)
MAX_AUDIO_BYTES = 30 * 1024 * 1024  # 30 MB

# TOEIC listening audio stored separately from music, served at /toeic-audio.
TOEIC_AUDIO_DIR = TOEIC_DIR / "audio"
TOEIC_AUDIO_DIR.mkdir(parents=True, exist_ok=True)

# --------------------------------------------------------------------------- #
# App + dependencies
# --------------------------------------------------------------------------- #
app = FastAPI(title="Knowledge Base")
app.mount("/static", StaticFiles(directory=str(STATIC)), name="static")
app.mount("/img", StaticFiles(directory=str(IMG_DIR)), name="img")
app.mount("/uploads/fonts", StaticFiles(directory=str(FONTS_DIR)), name="uploaded-fonts")
# Audio served at /audio so it doesn't shadow the /music/* app routes.
app.mount("/audio", StaticFiles(directory=str(MUSIC_DIR)), name="audio")
app.mount("/toeic-audio", StaticFiles(directory=str(TOEIC_AUDIO_DIR)), name="toeic-audio")
templates = Jinja2Templates(directory=str(TEMPLATES))

# Server-side markdown rendering for the detail view (no JS needed to read).
_md = mistune.create_markdown(
    escape=False,
    hard_wrap=True,
    plugins=["strikethrough", "table", "url", "task_lists"],
)
templates.env.filters["markdown"] = lambda text: _md(text or "")
templates.env.globals["theme"] = THEME


def _asset_version() -> int:
    """Max mtime of the CSS/JS — used to bust browser caches when they change.

    Registered as a callable so it's re-evaluated on every render: editing a
    static asset changes its mtime and the `?v=` query updates automatically,
    with no server restart needed.
    """
    try:
        return int(max(
            (STATIC / "style.css").stat().st_mtime,
            (STATIC / "app.js").stat().st_mtime,
        ))
    except OSError:
        return 0


templates.env.globals["asset_v"] = _asset_version

pm = PostManager(POSTS_DIR, DB_PATH)
tm = TagManager(POSTS_DIR)
toeic = ToeicManager(TOEIC_DIR)
books = BookManager(BOOKS_DIR)
music = MusicManager(MUSIC_DIR)
notes = NoteManager(NOTES_DIR)
api_docs = ApiDocsManager(API_DOCS_DIR)
bmarks = BookmarksManager(BOOKMARKS_DIR)
tasks_mgr = TaskManager(TASKS_DIR)
email_mgr = EmailManager(EMAILS_DIR)


def _parse_tags(raw: str) -> list[str]:
    return [t.strip() for t in raw.split(",") if t.strip()]


def _to_int(raw: str, default: int = 0) -> int:
    try:
        return int(str(raw).strip())
    except (ValueError, TypeError):
        return default


def _build_url(
    tags: list[str],
    q: str = "",
    status: str = "",
    category: str = "",
    page: int = 1,
) -> str:
    """Build a URL-encoded `/posts` URL preserving the active filter state."""
    params: list[tuple[str, str]] = [("tag", t) for t in tags]
    if q:
        params.append(("q", q))
    if status:
        params.append(("status", status))
    if category:
        params.append(("category", category))
    if page > 1:
        params.append(("page", str(page)))
    return "/posts?" + urlencode(params) if params else "/posts"


# --------------------------------------------------------------------------- #
# Homepage — feature boxes
# --------------------------------------------------------------------------- #
import json
LANG_PATH = _settings.db_path.parent / "language.json"

VI_LANG = {
    "title_main": "Cơ Sở Dữ Liệu",
    "title_sub": "Mọi thứ tại một nơi — chọn một mục để bắt đầu.",
    "apps": {
        "posts": {"title": "Bài Viết", "desc": "Ghi chú & bài viết với thẻ tag và tìm kiếm."},
        "series": {"title": "Chuỗi Bài", "desc": "Các chủ đề nhiều phần liên kết theo thứ tự."},
        "books": {"title": "Sách", "desc": "Bộ sưu tập các chương — tiểu thuyết & bài dài."},
        "toeic": {"title": "TOEIC", "desc": "Bộ đề thi với đáp án radio & giải thích."},
        "music": {"title": "Âm Nhạc", "desc": "Bản nhạc với siêu dữ liệu có thể chỉnh sửa."},
        "notes": {"title": "Ghi Chú Nhanh", "desc": "Ghi chú dạng hộp; ghim mục yêu thích."},
        "api-docs": {"title": "Tài Liệu API", "desc": "Tài liệu REST API — dự án, endpoints, params."},
        "bookmarks": {"title": "Dấu Trang", "desc": "Liên kết đã lưu được tổ chức theo thẻ."},
        "tasks": {"title": "Nhiệm Vụ", "desc": "Theo dõi công việc với các nhiệm vụ con."},
        "emails": {"title": "Soạn Email", "desc": "Soạn và dự thảo email dựa trên mẫu."},
        "dictionary": {"title": "Từ Điển", "desc": "Từ điển cá nhân lưu từ vựng, cụm từ."},
        "resume": {"title": "Hồ Sơ (CV)", "desc": "CV tương tác cập nhật hàng ngày & xuất PDF."}
    }
}

def get_language_dict():
    if not LANG_PATH.exists():
        return {"mode": "ENG", "dict": {}}
    try:
        config = json.loads(LANG_PATH.read_text("utf-8"))
        mode = config.get("mode", "ENG")
        if mode == "VI":
            return {"mode": mode, "dict": VI_LANG}
        elif mode == "CUSTOM":
            return {"mode": mode, "dict": config.get("custom", {})}
        return {"mode": "ENG", "dict": {}}
    except:
        return {"mode": "ENG", "dict": {}}

@app.get("/api/language")
def get_language():
    if not LANG_PATH.exists():
        return {"mode": "ENG", "custom": {}}
    try:
        return json.loads(LANG_PATH.read_text("utf-8"))
    except:
        return {"mode": "ENG", "custom": {}}

@app.post("/api/language")
async def save_language(request: Request):
    data = await request.json()
    LANG_PATH.parent.mkdir(parents=True, exist_ok=True)
    LANG_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), "utf-8")
    return {"status": "ok"}

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    lang_info = get_language_dict()
    ldict = lang_info["dict"]
    app_dict = ldict.get("apps", {})
    
    def get_app_text(app_id, default_title, default_desc):
        a = app_dict.get(app_id, {})
        return a.get("title", default_title), a.get("desc", default_desc)

    title_posts, desc_posts = get_app_text("posts", "Posts", "Notes & articles with tags and full-text search.")
    title_series, desc_series = get_app_text("series", "Series", "Multi-part topics linked in order.")
    title_books, desc_books = get_app_text("books", "Books", "Collections of chapters — novels & long reads.")
    title_toeic, desc_toeic = get_app_text("toeic", "TOEIC", "Practice sets with radio answers & explanations.")
    title_music, desc_music = get_app_text("music", "Music", "Imported tracks with editable metadata.")
    title_notes, desc_notes = get_app_text("notes", "Notes", "Quick notes shown as boxes; pin your favorites.")
    title_api, desc_api = get_app_text("api-docs", "API Docs", "Document REST APIs — projects, endpoints, params, responses.")
    title_bookmarks, desc_bookmarks = get_app_text("bookmarks", "Bookmarks", "Saved links organised by tags and category.")
    title_tasks, desc_tasks = get_app_text("tasks", "Tasks", "Task tracking with subtasks and version history.")
    title_emails, desc_emails = get_app_text("emails", "Email Composers", "Template-based email drafting and composing.")
    title_dict, desc_dict = get_app_text("dictionary", "Dictionary", "Personal dictionary to store words, phrases, and descriptions.")
    title_resume, desc_resume = get_app_text("resume", "Resume", "Interactive CV with daily skill updates and PDF export.")

    features = [
        {"icon": "📝", "app": "posts",    "title": title_posts,    "href": "/posts",
         "desc": desc_posts,
         "count": len(pm.list(status=None))},
        {"icon": "📚", "app": "series",   "title": title_series,   "href": "/series",
         "desc": desc_series,
         "count": len(pm.all_series())},
        {"icon": "📖", "app": "books",    "title": title_books,    "href": "/books",
         "desc": desc_books,
         "count": len(books.collections())},
        {"icon": "🎧", "app": "toeic",    "title": title_toeic,    "href": "/toeic",
         "desc": desc_toeic,
         "count": len(toeic.list())},
        {"icon": "🎵", "app": "music",    "title": title_music,    "href": "/music",
         "desc": desc_music,
         "count": len(music.list())},
        {"icon": "🗒️", "app": "notes",    "title": title_notes,    "href": "/notes",
         "desc": desc_notes,
         "count": len(notes.list())},
        {"icon": "📄", "app": "api-docs",   "title": title_api,   "href": "/api-docs",
         "desc": desc_api,
         "count": len(api_docs.list())},
        {"icon": "🔖", "app": "bookmarks", "title": title_bookmarks, "href": "/bookmarks",
         "desc": desc_bookmarks,
         "count": len(bmarks.list())},
        {"icon": "✅", "app": "tasks", "title": title_tasks, "href": "/tasks",
         "desc": desc_tasks,
         "count": len(tasks_mgr.list())},
        {"icon": "✉️", "app": "emails", "title": title_emails, "href": "/emails",
         "desc": desc_emails,
         "count": len(email_mgr.list())},
        {"icon": "📕", "app": "dictionary", "title": title_dict, "href": "/dictionary",
         "desc": desc_dict,
         "count": len(dict_db.get_words())},
        {"icon": "👔", "app": "resume", "title": title_resume, "href": "/resume",
         "desc": desc_resume,
         "count": 1},
    ]
    return templates.TemplateResponse(request, "home.html", {"features": features, "lang": ldict})



@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    icon = STATIC / "icon.png"
    if not icon.exists():
        raise HTTPException(404)
    return FileResponse(str(icon), media_type="image/png")


# --------------------------------------------------------------------------- #
# Posts list / feed
# --------------------------------------------------------------------------- #
@app.get("/posts", response_class=HTMLResponse)
async def list_posts(
    request: Request,
    tag: list[str] = Query(default=[]),
    q: str = "",
    status: str = "published",
    category: str = "",
    page: int = 1,
):
    active_tags = [t for t in tag if t]

    if q:
        slugs = pm.search.search(q, tags=active_tags or None, category=category or None)
        posts = [p for p in (pm.read(s) for s in slugs) if p]
        if status:
            posts = [p for p in posts if p.status.value == status]
    else:
        posts = pm.list(status=status or None)
        if active_tags:
            posts = [p for p in posts if all(t in p.tags for t in active_tags)]
        if category:
            posts = [p for p in posts if p.category == category]

    total = len(posts)
    pages = max(1, ceil(total / PAGE_SIZE)) if total else 1
    page = min(max(1, page), pages)
    start = (page - 1) * PAGE_SIZE
    page_posts = posts[start : start + PAGE_SIZE]

    # --- Facets with precomputed toggle URLs (URL-encoded state) ----------
    tag_cloud = []
    for name, count in tm.all_tags().items():
        is_active = name in active_tags
        toggled = [t for t in active_tags if t != name] if is_active else active_tags + [name]
        tag_cloud.append({
            "name": name,
            "count": count,
            "active": is_active,
            "url": _build_url(toggled, q=q, status=status, category=category),
        })

    cat_chips = []
    for name, count in pm.categories().items():
        is_active = name == category
        cat_chips.append({
            "name": name,
            "count": count,
            "active": is_active,
            "url": _build_url(active_tags, q=q, status=status,
                              category="" if is_active else name),
        })

    status_chips = [
        {
            "name": s,
            "active": s == status,
            "url": _build_url(active_tags, q=q,
                              status="" if s == status else s, category=category),
        }
        for s in ["published", "draft", "archived"]
    ]

    prev_url = _build_url(active_tags, q=q, status=status, category=category, page=page - 1) if page > 1 else None
    next_url = _build_url(active_tags, q=q, status=status, category=category, page=page + 1) if page < pages else None

    return templates.TemplateResponse(
        request,
        "list.html",
        {
            "posts": page_posts,
            "tag_cloud": tag_cloud,
            "cat_chips": cat_chips,
            "status_chips": status_chips,
            "q": q,
            "active_tags": active_tags,
            "status": status,
            "category": category,
            "page": page,
            "pages": pages,
            "total": total,
            "prev_url": prev_url,
            "next_url": next_url,
            "clear_url": _build_url([], status=status),
        },
    )


# --------------------------------------------------------------------------- #
# Series index
# --------------------------------------------------------------------------- #
@app.get("/series", response_class=HTMLResponse)
async def series_index(request: Request, sort: str = "az"):
    sort = sort if sort in ("az", "za") else "az"
    series = pm.all_series()  # already A–Z
    if sort == "za":
        series = list(reversed(series))
    return templates.TemplateResponse(
        request,
        "series_list.html",
        {"series": series, "sort": sort},
    )


# --------------------------------------------------------------------------- #
# Books (collections → chapters)
# --------------------------------------------------------------------------- #
@app.get("/books", response_class=HTMLResponse)
async def books_index(request: Request):
    return templates.TemplateResponse(
        request, "books_list.html", {"collections": books.collections()}
    )


@app.get("/books/new", response_class=HTMLResponse)
async def book_collection_new_form(request: Request):
    return templates.TemplateResponse(request, "book_collection_new.html", {})


@app.post("/books/new")
async def book_collection_create(
    title: str = Form(...),
    author: str = Form(""),
    description: str = Form(""),
    type: str = Form("written"),
    cover: str = Form(""),
    tags: str = Form(""),
):
    slug = books.create_collection(
        {
            "title": title,
            "author": author,
            "description": description,
            "type": type,
            "cover": cover,
            "tags": _parse_tags(tags),
        }
    )
    return RedirectResponse(f"/books/{slug}", status_code=303)


@app.get("/books/{coll}", response_class=HTMLResponse)
async def book_collection_detail(request: Request, coll: str):
    collection = books.read_collection(coll)
    if not collection:
        raise HTTPException(404)
    
    # If it's an imported book type, we want to show the resources on this page directly
    resources = books.list_resources(coll) if collection.type == "imported" else []
    
    return templates.TemplateResponse(
        request, "book_collection.html", {"collection": collection, "resources": resources}
    )


@app.get("/books/{coll}/edit", response_class=HTMLResponse)
async def book_collection_edit_form(request: Request, coll: str):
    collection = books.read_collection(coll, with_chapters=False)
    if not collection:
        raise HTTPException(404)
    return templates.TemplateResponse(
        request, "book_collection_edit.html", {"collection": collection}
    )


@app.post("/books/{coll}/edit")
async def book_collection_update(
    coll: str,
    title: str = Form(...),
    author: str = Form(""),
    description: str = Form(""),
    type: str = Form("written"),
    cover: str = Form(""),
    tags: str = Form(""),
):
    slug = books.update_collection(
        coll,
        {
            "title": title,
            "author": author,
            "description": description,
            "type": type,
            "cover": cover,
            "tags": _parse_tags(tags),
        },
    )
    if slug is None:
        raise HTTPException(404)
    return RedirectResponse(f"/books/{slug}", status_code=303)


@app.post("/books/{coll}/delete")
async def book_collection_delete(coll: str):
    if not books.delete_collection(coll):
        raise HTTPException(404)
    return RedirectResponse("/books", status_code=303)


@app.get("/books/{coll}/new", response_class=HTMLResponse)
async def book_chapter_new_form(request: Request, coll: str):
    collection = books.read_collection(coll, with_chapters=False)
    if not collection:
        raise HTTPException(404)
    next_order = len(books.chapters(coll)) + 1
    return templates.TemplateResponse(
        request,
        "book_chapter_new.html",
        {"collection": collection, "next_order": next_order},
    )


@app.post("/books/{coll}/new")
async def book_chapter_create(
    coll: str,
    title: str = Form(...),
    order: str = Form("0"),
    content: str = Form(""),
):
    slug = books.create_chapter(
        coll, {"title": title, "order": _to_int(order), "content": content}
    )
    if slug is None:
        raise HTTPException(404)
    return RedirectResponse(f"/books/{coll}/{slug}", status_code=303)


# --------------------------------------------------------------------------- #
# Book Resources (imported binary files: PDF, EPUB, MOBI, CBZ, ...)
# MUST be above /{coll}/{chapter} to avoid being captured by that catch-all.
# --------------------------------------------------------------------------- #

@app.get("/books/{coll}/resources", response_class=HTMLResponse)
async def book_resources_list(request: Request, coll: str):
    collection = books.read_collection(coll, with_chapters=False)
    if not collection:
        raise HTTPException(404)
    resources = books.list_resources(coll)
    return templates.TemplateResponse(
        request, "book_resources.html",
        {"collection": collection, "resources": resources}
    )


@app.post("/books/{coll}/resources/upload")
async def book_resource_upload(coll: str, file: UploadFile = File(...)):
    collection = books.read_collection(coll, with_chapters=False)
    if not collection:
        raise HTTPException(404)
    data = await file.read()
    ok = books.save_resource(coll, file.filename, data)
    if not ok:
        raise HTTPException(400, "Unsupported file type or collection not found.")
    return RedirectResponse(f"/books/{coll}/resources", status_code=303)


@app.get("/books/{coll}/resources/{fname}/page/{page_n}", response_class=Response)
async def book_resource_page_image(coll: str, fname: str, page_n: int):
    """Serve a single rendered page as a PNG image."""
    png = books.resource_page_image(coll, fname, page_n)
    if png is None:
        raise HTTPException(404)
    return Response(content=png, media_type="image/png")


@app.get("/books/{coll}/resources/{fname}/read", response_class=HTMLResponse)
async def book_resource_reader(request: Request, coll: str, fname: str, page: int = 0):
    collection = books.read_collection(coll, with_chapters=False)
    if not collection:
        raise HTTPException(404)
    resource_path = books._resource_path(coll, fname)
    if not resource_path.exists():
        raise HTTPException(404)

    from app.books import IMAGE_RENDER_FORMATS
    ext = resource_path.suffix.lower()
    is_image = ext in IMAGE_RENDER_FORMATS

    if is_image:
        total_pages = books.resource_page_count(coll, fname)
        page = max(0, min(page, total_pages - 1))
        return templates.TemplateResponse(
            request, "book_reader.html",
            {
                "collection": collection,
                "fname": fname,
                "mode": "image",
                "page": page,
                "total_pages": total_pages,
                "prev_page": page - 1 if page > 0 else None,
                "next_page": page + 1 if page < total_pages - 1 else None,
            }
        )
    else:
        chapters = books.resource_text_chapters(coll, fname)
        page = max(0, min(page, len(chapters) - 1))
        current_chapter = chapters[page] if chapters else {"title": "Empty", "html": ""}
        return templates.TemplateResponse(
            request, "book_reader.html",
            {
                "collection": collection,
                "fname": fname,
                "mode": "text",
                "page": page,
                "total_pages": len(chapters),
                "prev_page": page - 1 if page > 0 else None,
                "next_page": page + 1 if page < len(chapters) - 1 else None,
                "chapters": chapters,
                "current_chapter": current_chapter,
            }
        )


@app.post("/books/{coll}/resources/{fname}/delete")
async def book_resource_delete(coll: str, fname: str):
    if not books.delete_resource(coll, fname):
        raise HTTPException(404)
    return RedirectResponse(f"/books/{coll}/resources", status_code=303)


@app.get("/books/{coll}/{chapter}", response_class=HTMLResponse)
async def book_chapter_read(request: Request, coll: str, chapter: str):
    collection = books.read_collection(coll)
    if not collection:
        raise HTTPException(404)
    members = collection.chapters
    idx = next((i for i, c in enumerate(members) if c.slug == chapter), None)
    if idx is None:
        raise HTTPException(404)
    current = members[idx]
    content_html, toc = render_with_toc(current.content)
    return templates.TemplateResponse(
        request,
        "book_chapter.html",
        {
            "collection": collection,
            "chapter": current,
            "content_html": content_html,
            "toc": toc,
            "number": idx + 1,
            "total": len(members),
            "prev": members[idx - 1] if idx > 0 else None,
            "next": members[idx + 1] if idx < len(members) - 1 else None,
        },
    )



# --------------------------------------------------------------------------- #
# Email Composers
# --------------------------------------------------------------------------- #
@app.get("/emails", response_class=HTMLResponse)
async def emails_index(request: Request, q: str = "", category: str = ""):
    templates_list = email_mgr.list(q=q, category=category)
    categories = email_mgr.categories()
    return templates.TemplateResponse(
        request,
        "emails_list.html",
        {
            "templates": templates_list,
            "categories": categories,
            "q": q,
            "selected_category": category,
        },
    )


@app.get("/emails/new", response_class=HTMLResponse)
async def email_new_form(request: Request):
    return templates.TemplateResponse(request, "email_edit.html", {"template": None})


@app.post("/emails/new")
async def email_create(
    title: str = Form(...),
    subject: str = Form(...),
    category: str = Form("general"),
    description: str = Form(""),
    content: str = Form(""),
):
    slug = email_mgr.create(
        {
            "title": title,
            "subject": subject,
            "category": category,
            "description": description,
            "content": content,
        }
    )
    return RedirectResponse(f"/emails/{slug}", status_code=303)


@app.get("/emails/{slug}", response_class=HTMLResponse)
async def email_detail(request: Request, slug: str):
    tpl = email_mgr.read(slug)
    if not tpl:
        raise HTTPException(404, "Email template not found")
    return templates.TemplateResponse(request, "email_compose.html", {"template": tpl})


@app.get("/emails/{slug}/edit", response_class=HTMLResponse)
async def email_edit_form(request: Request, slug: str):
    tpl = email_mgr.read(slug)
    if not tpl:
        raise HTTPException(404, "Email template not found")
    if tpl.builtin:
        raise HTTPException(400, "Built-in templates cannot be edited")
    return templates.TemplateResponse(request, "email_edit.html", {"template": tpl})


@app.post("/emails/{slug}/edit")
async def email_update(
    slug: str,
    title: str = Form(...),
    subject: str = Form(...),
    category: str = Form("general"),
    description: str = Form(""),
    content: str = Form(""),
):
    tpl = email_mgr.read(slug)
    if not tpl:
        raise HTTPException(404, "Email template not found")
    if tpl.builtin:
        raise HTTPException(400, "Built-in templates cannot be edited")
    
    email_mgr.update(
        slug,
        {
            "title": title,
            "subject": subject,
            "category": category,
            "description": description,
            "content": content,
        }
    )
    return RedirectResponse(f"/emails/{slug}", status_code=303)


@app.post("/emails/{slug}/delete")
async def email_delete(slug: str):
    tpl = email_mgr.read(slug)
    if not tpl:
        raise HTTPException(404, "Email template not found")
    if tpl.builtin:
        raise HTTPException(400, "Built-in templates cannot be deleted")
    email_mgr.delete(slug)
    return RedirectResponse("/emails", status_code=303)



# --------------------------------------------------------------------------- #
# Music
# --------------------------------------------------------------------------- #
@app.get("/music", response_class=HTMLResponse)
async def music_index(request: Request):
    return templates.TemplateResponse(
        request, "music_list.html", {"tracks": music.list()}
    )


# ----- Playlists (registered before /music/{slug}/* so 'playlists' isn't a slug)
@app.get("/music/playlists", response_class=HTMLResponse)
async def playlists_index(request: Request):
    return templates.TemplateResponse(
        request, "playlists_list.html", {"playlists": music.list_playlists()}
    )


@app.get("/music/playlists/new", response_class=HTMLResponse)
async def playlist_new_form(request: Request):
    return templates.TemplateResponse(request, "playlist_edit.html", {})


@app.post("/music/playlists/new")
async def playlist_create(title: str = Form(...), description: str = Form("")):
    slug = music.create_playlist({"title": title, "description": description})
    return RedirectResponse(f"/music/playlists/{slug}", status_code=303)


@app.get("/music/playlists/{slug}", response_class=HTMLResponse)
async def playlist_detail(request: Request, slug: str):
    pl = music.read_playlist(slug)
    if not pl:
        raise HTTPException(404)
    in_pl = set(pl.track_slugs)
    available = [t for t in music.list() if t.slug not in in_pl]
    return templates.TemplateResponse(
        request, "playlist_detail.html", {"playlist": pl, "available": available}
    )


@app.post("/music/playlists/{slug}/add")
async def playlist_add(slug: str, track: str = Form(...)):
    if not music.add_to_playlist(slug, track):
        raise HTTPException(404)
    return RedirectResponse(f"/music/playlists/{slug}", status_code=303)


@app.post("/music/playlists/{slug}/remove")
async def playlist_remove(slug: str, track: str = Form(...)):
    if not music.remove_from_playlist(slug, track):
        raise HTTPException(404)
    return RedirectResponse(f"/music/playlists/{slug}", status_code=303)


@app.post("/music/playlists/{slug}/move")
async def playlist_move(slug: str, track: str = Form(...), direction: str = Form(...)):
    if direction not in ("up", "down") or not music.move_track(slug, track, direction):
        raise HTTPException(404)
    return RedirectResponse(f"/music/playlists/{slug}", status_code=303)


@app.post("/music/playlists/{slug}/delete")
async def playlist_delete(slug: str):
    if not music.delete_playlist(slug):
        raise HTTPException(404)
    return RedirectResponse("/music/playlists", status_code=303)


@app.post("/music/import")
async def music_import(file: UploadFile = File(...)):
    name = (file.filename or "").lower()
    ctype = (file.content_type or "").lower()
    is_mp3 = name.endswith(".mp3") or ctype in ("audio/mpeg", "audio/mp3")
    if not is_mp3:
        raise HTTPException(400, "Only .mp3 files are supported")
    data = await file.read()
    if not data:
        raise HTTPException(400, "Empty file")
    if len(data) > MAX_AUDIO_BYTES:
        raise HTTPException(413, "Audio too large (max 30 MB)")
    slug = music.import_track(file.filename or "track.mp3", data)
    return RedirectResponse(f"/music/{slug}/edit", status_code=303)


@app.get("/music/{slug}/edit", response_class=HTMLResponse)
async def music_edit_form(request: Request, slug: str):
    track = music.read(slug)
    if not track:
        raise HTTPException(404)
    return templates.TemplateResponse(request, "music_edit.html", {"track": track})


@app.post("/music/{slug}/edit")
async def music_update(
    slug: str,
    title: str = Form(...),
    author: str = Form(""),
    year: str = Form(""),
    type: str = Form(""),
    album: str = Form(""),
    cover: str = Form(""),
    notes: str = Form(""),
    lyrics: str = Form(""),
):
    updated = music.update(
        slug,
        {"title": title, "author": author, "year": year, "type": type,
         "album": album, "cover": cover, "notes": notes, "lyrics": lyrics},
    )
    if updated is None:
        raise HTTPException(404)
    return RedirectResponse("/music", status_code=303)


@app.post("/music/{slug}/delete")
async def music_delete(slug: str):
    if not music.delete(slug):
        raise HTTPException(404)
    return RedirectResponse("/music", status_code=303)


# --------------------------------------------------------------------------- #
# Notes (Title / date / content, pin-to-favorite)
# --------------------------------------------------------------------------- #
def _notes_url(tags: list[str], q: str = "") -> str:
    params = [("tag", t) for t in tags]
    if q:
        params.append(("q", q))
    return "/notes?" + urlencode(params) if params else "/notes"


@app.get("/notes", response_class=HTMLResponse)
async def notes_index(
    request: Request,
    tag: list[str] = Query(default=[]),
    q: str = "",
):
    active_tags = [t.lower().strip() for t in tag if t.strip()]
    items = notes.list(tags=active_tags or None, q=q)

    tag_cloud = []
    for name, count in notes.all_tags().items():
        is_active = name in active_tags
        toggled = [t for t in active_tags if t != name] if is_active else active_tags + [name]
        tag_cloud.append({
            "name": name, "count": count, "active": is_active,
            "url": _notes_url(toggled, q=q),
        })

    return templates.TemplateResponse(
        request,
        "notes_list.html",
        {
            "notes": items,
            "tag_cloud": tag_cloud,
            "active_tags": active_tags,
            "q": q,
            "clear_url": _notes_url([], q=q),
        },
    )


@app.get("/notes/export")
async def notes_export():
    import io
    import zipfile
    from fastapi.responses import StreamingResponse
    
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "a", zipfile.ZIP_DEFLATED, False) as zip_file:
        for f in NOTES_DIR.glob("*.md"):
            zip_file.writestr(f.name, f.read_text(encoding="utf-8"))
            
    zip_buffer.seek(0)
    return StreamingResponse(
        zip_buffer,
        media_type="application/zip",
        headers={"Content-Disposition": "attachment; filename=notes_export.zip"}
    )


@app.post("/notes/import")
async def notes_import(file: UploadFile = File(...)):
    import io
    import zipfile
    
    if not file.filename.endswith(".zip"):
        raise HTTPException(400, "Only ZIP files are supported.")
        
    content = await file.read()
    zip_buffer = io.BytesIO(content)
    
    try:
        with zipfile.ZipFile(zip_buffer, "r") as zip_file:
            for name in zip_file.namelist():
                if name.endswith(".md"):
                    file_content = zip_file.read(name)
                    safe_name = Path(name).name
                    (NOTES_DIR / safe_name).write_bytes(file_content)
    except Exception as e:
        raise HTTPException(400, f"Failed to extract zip: {e}")
        
    return RedirectResponse("/notes", status_code=303)


@app.post("/notes/import-md")
async def notes_import_md(files: list[UploadFile] = File(...)):
    for file in files:
        if not file.filename.endswith(".md"):
            continue
        content = await file.read()
        safe_name = Path(file.filename).name
        (NOTES_DIR / safe_name).write_bytes(content)
        
    return RedirectResponse("/notes", status_code=303)


@app.get("/notes/new", response_class=HTMLResponse)
async def note_new_form(request: Request):
    return templates.TemplateResponse(
        request, "note_edit.html", {"note": None, "themes": NOTE_THEMES}
    )


@app.post("/notes/new")
async def note_create(
    title: str = Form(...),
    date: str = Form(""),
    content: str = Form(""),
    tags: str = Form(""),
    theme: str = Form("plain"),
):
    slug = notes.create({
        "title": title, "date": date, "content": content,
        "tags": _parse_tags(tags), "theme": theme,
    })
    return RedirectResponse("/notes", status_code=303)


@app.get("/notes/{slug}", response_class=HTMLResponse)
async def note_detail(request: Request, slug: str):
    note = notes.read(slug)
    if not note:
        raise HTTPException(404)
    content_html, _ = render_with_toc(note.content)
    return templates.TemplateResponse(
        request, "note_detail.html", {"note": note, "content_html": content_html}
    )


@app.get("/notes/{slug}/edit", response_class=HTMLResponse)
async def note_edit_form(request: Request, slug: str):
    note = notes.read(slug)
    if not note:
        raise HTTPException(404)
    return templates.TemplateResponse(
        request, "note_edit.html", {"note": note, "themes": NOTE_THEMES}
    )


@app.post("/notes/{slug}/edit")
async def note_update(
    slug: str,
    title: str = Form(...),
    date: str = Form(""),
    content: str = Form(""),
    tags: str = Form(""),
    theme: str = Form("plain"),
):
    updated = notes.update(slug, {
        "title": title, "date": date, "content": content,
        "tags": _parse_tags(tags), "theme": theme,
    })
    if updated is None:
        raise HTTPException(404)
    return RedirectResponse("/notes", status_code=303)


@app.post("/notes/{slug}/pin")
async def note_pin(slug: str):
    if notes.toggle_pin(slug) is None:
        raise HTTPException(404)
    return RedirectResponse("/notes", status_code=303)


@app.post("/notes/{slug}/delete")
async def note_delete(slug: str):
    if not notes.delete(slug):
        raise HTTPException(404)
    return RedirectResponse("/notes", status_code=303)


# --------------------------------------------------------------------------- #
# API Documentation
# --------------------------------------------------------------------------- #
_API_SKELETON = """\
::: endpoint
method: GET
path: /items
title: List Items
description: Returns a paginated list of all items.

param: page    | query | integer | optional | Page number (default: 1)
param: limit   | query | integer | optional | Items per page (default: 20)
param: search  | query | string  | optional | Filter by name

response: 200 | Success
{
  "data": [{"id": 1, "name": "Example"}],
  "total": 100,
  "page": 1,
  "limit": 20
}

response: 401 | Unauthorized
{"error": "Authentication required"}
:::

::: endpoint
method: POST
path: /items
title: Create Item
description: Creates a new item.

param: name        | body | string  | required | Item name
param: description | body | string  | optional | Item description

response: 201 | Created
{"id": 42, "name": "New Item"}

response: 400 | Bad Request
{"error": "Validation failed", "details": {"name": "required"}}
:::
"""


@app.get("/api-docs", response_class=HTMLResponse)
async def api_docs_index(request: Request):
    return templates.TemplateResponse(
        request, "api_docs_list.html", {"projects": api_docs.list()}
    )


@app.get("/api-docs/new", response_class=HTMLResponse)
async def api_docs_new_form(request: Request):
    return templates.TemplateResponse(
        request, "api_docs_editor.html", {"project": None, "content": _API_SKELETON}
    )


@app.post("/api-docs/new")
async def api_docs_create(
    title: str = Form(...),
    base_url: str = Form(""),
    version: str = Form(""),
    description: str = Form(""),
    auth: str = Form(""),
    tags: str = Form(""),
    content: str = Form(""),
):
    slug = api_docs.create({
        "title": title, "base_url": base_url, "version": version,
        "description": description, "auth": auth,
        "tags": _parse_tags(tags), "content": content,
    })
    return RedirectResponse(f"/api-docs/{slug}", status_code=303)


@app.get("/api-docs/{slug}", response_class=HTMLResponse)
async def api_docs_detail(request: Request, slug: str):
    project = api_docs.read(slug)
    if not project:
        raise HTTPException(404)
    return templates.TemplateResponse(
        request, "api_docs_project.html", {"project": project}
    )


@app.get("/api-docs/{slug}/edit", response_class=HTMLResponse)
async def api_docs_edit_form(request: Request, slug: str):
    project = api_docs.read(slug)
    if not project:
        raise HTTPException(404)
    return templates.TemplateResponse(
        request, "api_docs_editor.html",
        {"project": project, "content": api_docs.raw_content(slug)}
    )


@app.post("/api-docs/{slug}/edit")
async def api_docs_update(
    slug: str,
    title: str = Form(...),
    base_url: str = Form(""),
    version: str = Form(""),
    description: str = Form(""),
    auth: str = Form(""),
    tags: str = Form(""),
    content: str = Form(""),
):
    if api_docs.update(slug, {
        "title": title, "base_url": base_url, "version": version,
        "description": description, "auth": auth,
        "tags": _parse_tags(tags), "content": content,
    }) is None:
        raise HTTPException(404)
    return RedirectResponse(f"/api-docs/{slug}", status_code=303)


@app.post("/api-docs/{slug}/delete")
async def api_docs_delete(slug: str):
    if not api_docs.delete(slug):
        raise HTTPException(404)
    return RedirectResponse("/api-docs", status_code=303)


# --------------------------------------------------------------------------- #
# Bookmarks
# --------------------------------------------------------------------------- #
def _bm_url(tags: list[str], q: str = "", category: str = "") -> str:
    from urllib.parse import urlencode as _ue
    params: list[tuple[str, str]] = [("tag", t) for t in tags]
    if q:
        params.append(("q", q))
    if category:
        params.append(("category", category))
    return "/bookmarks?" + _ue(params) if params else "/bookmarks"


@app.get("/bookmarks", response_class=HTMLResponse)
async def bookmarks_index(
    request: Request,
    tag: list[str] = Query(default=[]),
    q: str = "",
    category: str = "",
):
    active_tags = [t.lower().strip() for t in tag if t.strip()]
    items = bmarks.list(tags=active_tags or None, q=q, category=category)

    tag_cloud = []
    for name, count in bmarks.all_tags().items():
        is_active = name in active_tags
        toggled = [t for t in active_tags if t != name] if is_active else active_tags + [name]
        tag_cloud.append({
            "name": name, "count": count, "active": is_active,
            "url": _bm_url(toggled, q=q, category=category),
        })

    cats = bmarks.all_categories()

    return templates.TemplateResponse(
        request, "bookmarks_list.html",
        {
            "bookmarks": items,
            "tag_cloud": tag_cloud,
            "active_tags": active_tags,
            "categories": cats,
            "active_category": category,
            "q": q,
            "clear_url": _bm_url([]),
        },
    )


@app.get("/bookmarks/new", response_class=HTMLResponse)
async def bookmark_new_form(request: Request):
    categories = bmarks.all_categories()
    return templates.TemplateResponse(
        request, "bookmark_edit.html", {"bm": None, "categories": categories}
    )


@app.post("/bookmarks/new")
async def bookmark_create(
    title: str = Form(...),
    url: str = Form(...),
    description: str = Form(""),
    tags: str = Form(""),
    category: str = Form(""),
    notes: str = Form(""),
):
    slug = bmarks.create({
        "title": title, "url": url, "description": description,
        "tags": _parse_tags(tags), "category": category.strip(), "notes": notes,
    })
    return RedirectResponse("/bookmarks", status_code=303)


@app.get("/bookmarks/{slug}/edit", response_class=HTMLResponse)
async def bookmark_edit_form(request: Request, slug: str):
    bm = bmarks.read(slug)
    if not bm:
        raise HTTPException(404)
    return templates.TemplateResponse(
        request, "bookmark_edit.html",
        {"bm": bm, "categories": bmarks.all_categories()}
    )


@app.post("/bookmarks/{slug}/edit")
async def bookmark_update(
    slug: str,
    title: str = Form(...),
    url: str = Form(...),
    description: str = Form(""),
    tags: str = Form(""),
    category: str = Form(""),
    notes: str = Form(""),
):
    if bmarks.update(slug, {
        "title": title, "url": url, "description": description,
        "tags": _parse_tags(tags), "category": category.strip(), "notes": notes,
    }) is None:
        raise HTTPException(404)
    return RedirectResponse("/bookmarks", status_code=303)


@app.post("/bookmarks/{slug}/pin")
async def bookmark_pin(slug: str):
    if bmarks.toggle_pin(slug) is None:
        raise HTTPException(404)
    return RedirectResponse("/bookmarks", status_code=303)


@app.post("/bookmarks/{slug}/delete")
async def bookmark_delete(slug: str):
    if not bmarks.delete(slug):
        raise HTTPException(404)
    return RedirectResponse("/bookmarks", status_code=303)


# --------------------------------------------------------------------------- #
# Tasks
# --------------------------------------------------------------------------- #

@app.get("/tasks", response_class=HTMLResponse)
def get_tasks(request: Request, q: str = ""):
    tsks = tasks_mgr.list(q=q)
    return templates.TemplateResponse(request, "tasks_list.html", {
        "tasks": tsks, "q": q
    })


@app.get("/tasks/new", response_class=HTMLResponse)
def new_task_form(request: Request):
    return templates.TemplateResponse(request, "task_edit.html", {"task": None})


@app.post("/tasks/new")
async def create_task(request: Request):
    form = await request.form()
    
    subtasks = []
    i = 0
    # form entries might be unordered or missing due to JS removing items,
    # so we iterate through all keys to find st_title_*
    st_keys = [k for k in form.keys() if k.startswith("st_title_")]
    for k in st_keys:
        idx = k.replace("st_title_", "")
        t = form.get(f"st_title_{idx}", "").strip()
        s = form.get(f"st_status_{idx}", "to-do")
        n = form.get(f"st_notes_{idx}", "").strip()
        if t:
            subtasks.append({"title": t, "status": s, "notes": n})
            
    slug = tasks_mgr.create({
        "title": form.get("title", ""),
        "user": form.get("user", ""),
        "content": form.get("content", ""),
        "subtasks": subtasks
    })
    return RedirectResponse(f"/tasks/{slug}", status_code=303)


@app.get("/tasks/{slug}", response_class=HTMLResponse)
def view_task(request: Request, slug: str, v: int | None = None):
    task = tasks_mgr.read(slug)
    if not task:
        raise HTTPException(404)
        
    if v is not None:
        version = tasks_mgr.read_version(slug, v)
        if not version:
            raise HTTPException(404)
        is_latest = (version.version == task.latest.version)
    else:
        version = task.latest
        is_latest = True
        
    return templates.TemplateResponse(request, "task_detail.html", {
        "task": task,
        "version": version,
        "is_latest": is_latest
    })


@app.get("/tasks/{slug}/edit", response_class=HTMLResponse)
def edit_task_form(request: Request, slug: str):
    task = tasks_mgr.read(slug)
    if not task:
        raise HTTPException(404)
    return templates.TemplateResponse(request, "task_edit.html", {"task": task})


@app.post("/tasks/{slug}/edit")
async def edit_task(request: Request, slug: str):
    form = await request.form()
    
    subtasks = []
    st_keys = [k for k in form.keys() if k.startswith("st_title_")]
    for k in st_keys:
        idx = k.replace("st_title_", "")
        t = form.get(f"st_title_{idx}", "").strip()
        s = form.get(f"st_status_{idx}", "to-do")
        n = form.get(f"st_notes_{idx}", "").strip()
        if t:
            subtasks.append({"title": t, "status": s, "notes": n})
        
    tasks_mgr.update(slug, {
        "title": form.get("title", ""),
        "user": form.get("user", ""),
        "content": form.get("content", ""),
        "subtasks": subtasks
    })
    return RedirectResponse(f"/tasks/{slug}", status_code=303)


@app.post("/tasks/{slug}/delete")
def delete_task(slug: str):
    if not tasks_mgr.delete(slug):
        raise HTTPException(404)
    return RedirectResponse("/tasks", status_code=303)


@app.post("/tasks/{slug}/v/{version}/delete")
def delete_task_version(slug: str, version: int):
    if not tasks_mgr.delete_version(slug, version):
        raise HTTPException(404)
    if not tasks_mgr.read(slug):
        return RedirectResponse("/tasks", status_code=303)
    return RedirectResponse(f"/tasks/{slug}", status_code=303)


# --------------------------------------------------------------------------- #
# TOEIC audio upload
# --------------------------------------------------------------------------- #
ALLOWED_AUDIO_TYPES = {
    "audio/mpeg": ".mp3", "audio/mp3": ".mp3",
    "audio/ogg": ".ogg", "audio/wav": ".wav", "audio/x-wav": ".wav",
    "audio/aac": ".aac", "audio/m4a": ".m4a", "audio/mp4": ".m4a",
}


@app.post("/api/upload-audio")
async def upload_toeic_audio(file: UploadFile = File(...)):
    ext = ALLOWED_AUDIO_TYPES.get((file.content_type or "").lower())
    name = (file.filename or "").lower()
    if not ext:
        # fallback: detect by file extension
        for e in (".mp3", ".ogg", ".wav", ".aac", ".m4a"):
            if name.endswith(e):
                ext = e
                break
    if not ext:
        raise HTTPException(400, f"Unsupported audio type: {file.content_type!r}")
    data = await file.read()
    if not data:
        raise HTTPException(400, "Empty file")
    if len(data) > MAX_AUDIO_BYTES:
        raise HTTPException(413, "Audio too large (max 30 MB)")
    digest = hashlib.sha256(data).hexdigest()[:16]
    filename = f"{digest}{ext}"
    TOEIC_AUDIO_DIR.mkdir(parents=True, exist_ok=True)
    path = TOEIC_AUDIO_DIR / filename
    if not path.exists():
        path.write_bytes(data)
    return {"url": f"/toeic-audio/{filename}", "filename": filename}


# --------------------------------------------------------------------------- #
# TOEIC Listening (Parts 1-4)
# --------------------------------------------------------------------------- #
_L_SKELETONS = {
    1: """\
::: photo
image: /img/your-photo.jpg
audio: /toeic-audio/p1-q1.mp3
- A. A woman is sitting at a desk.
- B. A man is standing near a window.
- C. The books are stacked on the floor.
- D. A lamp is placed on a table.
answer: A
note: (A) best describes the photograph — the woman is clearly seated at her desk.
:::
""",
    2: """\
::: qr
audio: /toeic-audio/p2-q1.mp3
transcript: "Have you reviewed the quarterly report yet?"
- A. Yes, I finished it this morning.
- B. No, the office is on the second floor.
- C. It takes about thirty minutes.
answer: A
note: Only (A) directly answers whether the report has been reviewed.
:::
""",
    3: """\
::: group
audio: /toeic-audio/p3-c1.mp3

Man: I'd like to book a conference room for Friday afternoon.
Woman: We have Room A available from 2 to 5 PM.
Man: Perfect. I'll need a projector as well.

::: cq
What does the man want to do?
- A. Attend a conference
- B. Reserve a meeting room
- C. Buy a projector
- D. Schedule a training
answer: B
note: "I'd like to book a conference room" clearly shows he wants to reserve a room.
:::

::: cq
When is the room available?
- A. Friday morning
- B. Friday afternoon
- C. Saturday afternoon
- D. Monday morning
answer: B
:::

::: cq
What equipment does the man request?
- A. A whiteboard
- B. A computer
- C. A projector
- D. A microphone
answer: C
:::
:::
""",
    4: """\
::: group
audio: /toeic-audio/p4-t1.mp3

Good morning, everyone. I'm calling to remind you that our annual
company picnic will be held this Saturday at Riverside Park. The event
starts at 11 AM and will end around 4 PM. Please bring your own chairs.

::: cq
What is the announcement about?
- A. A business meeting
- B. A company picnic
- C. A training session
- D. A product launch
answer: B
:::

::: cq
Where will the event take place?
- A. At the office
- B. At a conference center
- C. At Riverside Park
- D. At the speaker's home
answer: C
:::

::: cq
What are listeners asked to bring?
- A. Food and drinks
- B. Their laptops
- C. Their own chairs
- D. Identification cards
answer: C
:::
:::
""",
}


@app.get("/toeic/listening", response_class=HTMLResponse)
async def listening_index(request: Request):
    return templates.TemplateResponse(
        request, "listening_list.html", {"sets": toeic.list_listening()}
    )


@app.get("/toeic/listening/new", response_class=HTMLResponse)
async def listening_new_form(request: Request, part: int = 1):
    part = part if part in (1, 2, 3, 4) else 1
    return templates.TemplateResponse(
        request, "listening_editor.html",
        {"lset": None, "default_body": _L_SKELETONS[part], "default_part": part},
    )


@app.post("/toeic/listening/new")
async def listening_create(
    title: str = Form(...),
    part: str = Form("1"),
    format: str = Form("new"),
    summary: str = Form(""),
    content: str = Form(""),
):
    slug = toeic.create_listening({
        "title": title, "part": _to_int(part, 1), "format": format,
        "summary": summary, "content": content,
    })
    return RedirectResponse(f"/toeic/listening/{slug}", status_code=303)


@app.get("/toeic/listening/{slug}", response_class=HTMLResponse)
async def listening_detail(request: Request, slug: str):
    lset = toeic.read_listening(slug)
    if not lset:
        raise HTTPException(404)
    return templates.TemplateResponse(
        request, "listening_detail.html", {"lset": lset}
    )


@app.get("/toeic/listening/{slug}/edit", response_class=HTMLResponse)
async def listening_edit_form(request: Request, slug: str):
    lset = toeic.read_listening(slug)
    if not lset:
        raise HTTPException(404)
    content = toeic.raw_listening(slug)
    return templates.TemplateResponse(
        request, "listening_editor.html",
        {"lset": lset, "default_body": content, "default_part": lset.part},
    )


@app.post("/toeic/listening/{slug}/edit")
async def listening_update(
    slug: str,
    title: str = Form(...),
    part: str = Form("1"),
    format: str = Form("new"),
    summary: str = Form(""),
    content: str = Form(""),
):
    lset = toeic.read_listening(slug)
    if not lset:
        raise HTTPException(404)
    today = __import__("datetime").date.today().isoformat()
    import frontmatter as _fm
    meta = {
        "type": "listening",
        "title": title.strip(),
        "part": _to_int(part, 1),
        "format": format if format in ("old", "new") else "new",
        "summary": summary.strip(),
        "created": lset.created or today,
        "updated": today,
    }
    fm = _fm.Post(content, **meta)
    toeic._l_path(slug).write_text(_fm.dumps(fm), encoding="utf-8")
    return RedirectResponse(f"/toeic/listening/{slug}", status_code=303)


# --------------------------------------------------------------------------- #
# TOEIC practice
# --------------------------------------------------------------------------- #
@app.get("/toeic", response_class=HTMLResponse)
async def toeic_index(request: Request):
    sets = toeic.list()
    return templates.TemplateResponse(
        request, "toeic_list.html", {"sets": sets}
    )


TOEIC_SKELETON = """\
::: question
The board will _____ the proposal next week.
- A. review
- B. reviews
- C. reviewing
- D. reviewed
answer: A
note: After the modal **will**, use the base form.
:::
"""


@app.get("/toeic/new", response_class=HTMLResponse)
async def toeic_new_form(request: Request):
    return templates.TemplateResponse(
        request, "toeic_editor.html", {"set": None, "default_body": TOEIC_SKELETON}
    )


@app.post("/toeic/new")
async def toeic_create(
    title: str = Form(...),
    part: str = Form("5"),
    tags: str = Form(""),
    summary: str = Form(""),
    content: str = Form(""),
):
    slug = toeic.create(
        {
            "title": title,
            "part": _to_int(part, 5),
            "tags": _parse_tags(tags),
            "summary": summary,
            "content": content,
        }
    )
    return RedirectResponse(f"/toeic/{slug}", status_code=303)


@app.get("/toeic/{slug}", response_class=HTMLResponse)
async def toeic_detail(request: Request, slug: str):
    tset = toeic.read(slug)
    if not tset:
        raise HTTPException(404)
    return templates.TemplateResponse(
        request, "toeic_detail.html", {"set": tset}
    )


# --------------------------------------------------------------------------- #
# Detail
# --------------------------------------------------------------------------- #
@app.get("/posts/{slug}", response_class=HTMLResponse)
async def detail(request: Request, slug: str):
    post = pm.read(slug)
    if not post:
        raise HTTPException(404)
    content_html, toc = render_with_toc(post.content)

    series_nav = None
    if post.series:
        members = pm.series(post.series)
        idx = next((i for i, p in enumerate(members) if p.slug == post.slug), None)
        if idx is not None:
            series_nav = {
                "name": post.series,
                "members": members,
                "current": post.slug,
                "number": idx + 1,
                "total": len(members),
                "prev": members[idx - 1] if idx > 0 else None,
                "next": members[idx + 1] if idx < len(members) - 1 else None,
            }

    return templates.TemplateResponse(
        request,
        "detail.html",
        {"post": post, "content_html": content_html, "toc": toc, "series": series_nav},
    )


# --------------------------------------------------------------------------- #
# Create
# --------------------------------------------------------------------------- #
@app.get("/new", response_class=HTMLResponse)
async def new_form(request: Request):
    return templates.TemplateResponse(request, "editor.html", {"post": None})


@app.post("/new")
async def create_post(
    title: str = Form(...),
    content: str = Form(""),
    tags: str = Form(""),
    category: str = Form("General"),
    status: str = Form("published"),
    summary: str = Form(""),
    series: str = Form(""),
    series_order: str = Form("0"),
):
    post = pm.create(
        {
            "title": title,
            "content": content,
            "tags": _parse_tags(tags),
            "category": category,
            "status": status,
            "summary": summary,
            "series": series.strip(),
            "series_order": _to_int(series_order),
            "created": date.today(),
            "updated": date.today(),
        }
    )
    tm.rebuild()
    return RedirectResponse(f"/posts/{post.slug}", status_code=303)


# --------------------------------------------------------------------------- #
# Edit
# --------------------------------------------------------------------------- #
@app.get("/edit/{slug}", response_class=HTMLResponse)
async def edit_form(request: Request, slug: str):
    post = pm.read(slug)
    if not post:
        raise HTTPException(404)
    return templates.TemplateResponse(request, "editor.html", {"post": post})


@app.post("/edit/{slug}")
async def update_post(
    slug: str,
    title: str = Form(...),
    content: str = Form(""),
    tags: str = Form(""),
    category: str = Form("General"),
    status: str = Form("published"),
    summary: str = Form(""),
    series: str = Form(""),
    series_order: str = Form("0"),
):
    updated = pm.update(
        slug,
        {
            "title": title,
            "content": content,
            "tags": _parse_tags(tags),
            "category": category,
            "status": status,
            "summary": summary,
            "series": series.strip(),
            "series_order": _to_int(series_order),
            "updated": date.today(),
        },
    )
    if not updated:
        raise HTTPException(404)
    tm.rebuild()
    return RedirectResponse(f"/posts/{slug}", status_code=303)


# --------------------------------------------------------------------------- #
# Delete
# --------------------------------------------------------------------------- #
@app.delete("/posts/{slug}")
async def delete_post(slug: str):
    if not pm.delete(slug):
        raise HTTPException(404)
    tm.rebuild()
    return {"ok": True}


# --------------------------------------------------------------------------- #
# Import / Export
# --------------------------------------------------------------------------- #
@app.post("/posts/import")
async def import_posts(files: list[UploadFile] = File(...)):
    for file in files:
        if not file.filename.endswith(".md"):
            continue
        content = await file.read()
        safe_name = Path(file.filename).name
        (POSTS_DIR / safe_name).write_bytes(content)
        
    pm.rebuild_index()
    tm.rebuild()
    return RedirectResponse("/", status_code=303)


@app.get("/posts/{slug}/export")
async def export_post(slug: str):
    post = pm.read(slug)
    if not post:
        raise HTTPException(404)
    post_path = POSTS_DIR / f"{slug}.md"
    if not post_path.exists():
        raise HTTPException(404)
    return FileResponse(
        path=post_path, 
        filename=post_path.name,
        media_type="text/markdown"
    )


# --------------------------------------------------------------------------- #
# Search API (JSON) – used by the live search bar
# --------------------------------------------------------------------------- #
@app.get("/api/search")
async def api_search(
    q: str = "",
    tag: list[str] = Query(default=[]),
    category: str = "",
):
    active_tags = [t for t in tag if t]
    hits = pm.search.search_snippets(
        q, tags=active_tags or None, category=category or None
    )
    out = []
    for hit in hits:
        post = pm.read(hit["slug"])
        if not post:
            continue
        data = post.model_dump(exclude={"content"}, mode="json")
        data["snippet"] = hit["snippet"]
        out.append(data)
    return out


# --------------------------------------------------------------------------- #
# Image upload (paste-into-editor) – stores in img/ and returns a markdown URL
# --------------------------------------------------------------------------- #
@app.post("/api/upload")
async def upload_image(file: UploadFile = File(...)):
    ext = ALLOWED_IMAGE_TYPES.get((file.content_type or "").lower())
    if not ext:
        raise HTTPException(400, f"Unsupported image type: {file.content_type!r}")

    data = await file.read()
    if not data:
        raise HTTPException(400, "Empty file")
    if len(data) > MAX_IMAGE_BYTES:
        raise HTTPException(413, "Image too large (max 10 MB)")

    # Content-addressed name: identical pastes dedupe, names never collide.
    digest = hashlib.sha256(data).hexdigest()[:16]
    filename = f"{digest}{ext}"
    IMG_DIR.mkdir(parents=True, exist_ok=True)
    path = IMG_DIR / filename
    if not path.exists():
        path.write_bytes(data)

    url = f"/img/{filename}"
    return {"url": url, "markdown": f"![]({url})", "filename": filename}


@app.post("/api/upload-icon")
async def upload_icon(file: UploadFile = File(...)):
    """Upload a custom app icon; stored in img/icons/ and served at /img/icons/…"""
    ext = ALLOWED_IMAGE_TYPES.get((file.content_type or "").lower())
    name = (file.filename or "").lower()
    if not ext:
        for e in (".png", ".jpg", ".jpeg", ".webp", ".gif", ".svg", ".bmp"):
            if name.endswith(e):
                ext = e if e != ".jpeg" else ".jpg"
                break
    if not ext:
        raise HTTPException(400, f"Unsupported image type: {file.content_type!r}")
    data = await file.read()
    if not data:
        raise HTTPException(400, "Empty file")
    if len(data) > MAX_IMAGE_BYTES:
        raise HTTPException(413, "Image too large (max 10 MB)")
    digest = hashlib.sha256(data).hexdigest()[:16]
    filename = f"{digest}{ext}"
    icon_dir = IMG_DIR / "icons"
    icon_dir.mkdir(parents=True, exist_ok=True)
    path = icon_dir / filename
    if not path.exists():
        path.write_bytes(data)
    return {"url": f"/img/icons/{filename}", "filename": filename}


@app.get("/api/icons")
async def list_icons():
    """Return all uploaded app icons in img/icons/."""
    icon_dir = IMG_DIR / "icons"
    if not icon_dir.exists():
        return []
    allowed_ext = {".png", ".jpg", ".jpeg", ".webp", ".gif", ".svg", ".bmp"}
    files = sorted(
        (f for f in icon_dir.iterdir() if f.is_file() and f.suffix.lower() in allowed_ext),
        key=lambda f: f.stat().st_mtime,
        reverse=True,
    )
    return [{"url": f"/img/icons/{f.name}", "filename": f.name} for f in files]


@app.delete("/api/icons/{filename}")
async def delete_icon(filename: str):
    """Delete an uploaded app icon from img/icons/."""
    # Reject anything with path traversal characters
    if "/" in filename or "\\" in filename or ".." in filename:
        raise HTTPException(400, "Invalid filename")
    path = IMG_DIR / "icons" / filename
    if not path.exists():
        raise HTTPException(404, "Icon not found")
    path.unlink()
    return {"ok": True}


# ---------------------------------------------------------------------------
# Background management  (img/background/)
# ---------------------------------------------------------------------------

@app.post("/api/upload-background")
async def upload_background(file: UploadFile = File(...)):
    """Upload a background image; stored in img/background/ and served at /img/background/…"""
    ext = ALLOWED_IMAGE_TYPES.get((file.content_type or "").lower())
    name = (file.filename or "").lower()
    if not ext:
        for e in (".png", ".jpg", ".jpeg", ".webp", ".gif", ".svg", ".bmp"):
            if name.endswith(e):
                ext = e if e != ".jpeg" else ".jpg"
                break
    if not ext:
        raise HTTPException(400, f"Unsupported image type: {file.content_type!r}")
    data = await file.read()
    if not data:
        raise HTTPException(400, "Empty file")
    if len(data) > MAX_IMAGE_BYTES:
        raise HTTPException(413, "Image too large (max 10 MB)")
    digest = hashlib.sha256(data).hexdigest()[:16]
    filename = f"{digest}{ext}"
    path = BG_DIR / filename
    if not path.exists():
        path.write_bytes(data)
    return {"url": f"/img/background/{filename}", "filename": filename}


@app.get("/api/backgrounds")
async def list_backgrounds():
    """Return all uploaded background images in img/background/."""
    allowed_ext = {".png", ".jpg", ".jpeg", ".webp", ".gif", ".svg", ".bmp"}
    files = sorted(
        (f for f in BG_DIR.iterdir() if f.is_file() and f.suffix.lower() in allowed_ext),
        key=lambda f: f.stat().st_mtime,
        reverse=True,
    )
    return [{"url": f"/img/background/{f.name}", "filename": f.name} for f in files]


@app.delete("/api/backgrounds/{filename}")
async def delete_background(filename: str):
    """Delete an uploaded background image from img/background/."""
    if "/" in filename or "\\" in filename or ".." in filename:
        raise HTTPException(400, "Invalid filename")
    path = BG_DIR / filename
    if not path.exists():
        raise HTTPException(404, "Background not found")
    path.unlink()
    return {"ok": True}


# -----------------------------------------------------------------------------
# Fonts Management API
# -----------------------------------------------------------------------------

@app.post("/api/fonts")
async def upload_font(file: UploadFile = File(...)):
    """Upload a custom font file; stored in fonts/ and served at /uploads/fonts/…"""
    ext = ""
    name = (file.filename or "").lower()
    for e in (".ttf", ".woff", ".woff2", ".otf"):
        if name.endswith(e):
            ext = e
            break
    if not ext:
        raise HTTPException(400, "Unsupported font type (use .ttf, .otf, .woff, .woff2)")
    
    data = await file.read()
    if not data:
        raise HTTPException(400, "Empty file")
    if len(data) > 10 * 1024 * 1024:  # 10 MB limit for fonts
        raise HTTPException(413, "Font file too large (max 10 MB)")
    
    digest = hashlib.sha256(data).hexdigest()[:16]
    filename = f"{digest}{ext}"
    path = FONTS_DIR / filename
    if not path.exists():
        path.write_bytes(data)
    
    # Extract font family name (basic fallback to filename minus extension)
    font_name = file.filename.rsplit('.', 1)[0].replace('-', ' ').replace('_', ' ').title()
    
    return {
        "url": f"/uploads/fonts/{filename}",
        "filename": filename,
        "label": font_name
    }


@app.get("/api/fonts")
async def list_fonts():
    """Return all uploaded font files."""
    allowed_ext = {".ttf", ".woff", ".woff2", ".otf"}
    files = sorted(
        (f for f in FONTS_DIR.iterdir() if f.is_file() and f.suffix.lower() in allowed_ext),
        key=lambda f: f.stat().st_mtime,
        reverse=True,
    )
    return [
        {
            "url": f"/uploads/fonts/{f.name}",
            "filename": f.name,
            "label": f.name.rsplit('.', 1)[0]
        }
        for f in files
    ]


@app.delete("/api/fonts/{filename}")
async def delete_font(filename: str):
    """Delete an uploaded font."""
    if "/" in filename or "\\" in filename or ".." in filename:
        raise HTTPException(400, "Invalid filename")
    path = FONTS_DIR / filename
    if not path.exists():
        raise HTTPException(404, "Font not found")
    path.unlink()
    return {"ok": True}


# -----------------------------------------------------------------------------
# Self Dictionary API
# -----------------------------------------------------------------------------

class DictionaryEntry(BaseModel):
    word: str
    description: str
    tags: list[str] = []

@app.get("/dictionary")
async def dictionary_page(request: Request):
    """Render the Dictionary page."""
    return templates.TemplateResponse(request, "dictionary.html", {})

@app.get("/api/dictionary")
async def get_dictionary(search: str = "", sort_dir: str = "asc", page: int = 1, limit: int = 25):
    """Get all dictionary entries with search and sort."""
    offset = (page - 1) * limit
    words_data = dict_db.get_words(search=search, sort_dir=sort_dir, limit=limit, offset=offset)
    return words_data

@app.post("/api/dictionary")
async def create_dictionary_entry(entry: DictionaryEntry):
    """Add a new word to the dictionary."""
    dict_id = dict_db.add_word(entry.word, entry.description, entry.tags)
    return {"id": dict_id, "status": "success"}

@app.put("/api/dictionary/{dict_id}")
async def update_dictionary_entry(dict_id: int, entry: DictionaryEntry):
    """Update an existing word."""
    success = dict_db.update_word(dict_id, entry.word, entry.description, entry.tags)
    if not success:
        raise HTTPException(404, "Entry not found")
    return {"status": "success"}

@app.delete("/api/dictionary/{dict_id}")
async def delete_dictionary_entry(dict_id: int):
    """Delete a word."""
    success = dict_db.delete_word(dict_id)
    if not success:
        raise HTTPException(404, "Entry not found")
    return {"status": "success"}

# --------------------------------------------------------------------------- #
# Resume
# --------------------------------------------------------------------------- #
import frontmatter as _fm

RESUME_PATH = POSTS_DIR.parent / "resume" / "resume.md"

@app.get("/resume", response_class=HTMLResponse)
async def resume_view(request: Request):
    if not RESUME_PATH.exists():
        RESUME_PATH.parent.mkdir(exist_ok=True)
        RESUME_PATH.write_text("---\nname: Your Name\n---\nBio", encoding="utf-8")
    
    fm = _fm.load(RESUME_PATH)
    content_html, _ = render_with_toc(fm.content)
    return templates.TemplateResponse(
        request, "resume.html", {"resume": fm.metadata, "content_html": content_html}
    )

@app.get("/resume/edit", response_class=HTMLResponse)
async def resume_edit_form(request: Request):
    if not RESUME_PATH.exists():
        RESUME_PATH.parent.mkdir(exist_ok=True)
        RESUME_PATH.write_text("---\nname: Your Name\n---\nBio", encoding="utf-8")
    
    fm = _fm.load(RESUME_PATH)
    return templates.TemplateResponse(
        request, "resume_editor.html", {"resume": fm.metadata, "content": fm.content}
    )

@app.post("/resume/save")
async def resume_save(request: Request):
    data = await request.json()
    metadata = data.get("metadata", {})
    content = data.get("content", "")
    
    post = _fm.Post(content, **metadata)
    RESUME_PATH.write_text(_fm.dumps(post), encoding="utf-8")
    return {"ok": True}

@app.get("/resume/export.md")
async def resume_export_md():
    if not RESUME_PATH.exists():
        raise HTTPException(404)
    return FileResponse(
        path=RESUME_PATH, 
        filename="resume.md",
        media_type="text/markdown"
    )

