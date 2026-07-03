"""FastAPI application – routes, templates, and markdown rendering.

Paths are resolved so the app works both in development and inside a
PyInstaller bundle (Phase 5). Configuration is read from `config.yaml`.
"""

from __future__ import annotations

import hashlib
import mimetypes
from datetime import date
from math import ceil
from urllib.parse import urlencode

import mistune
from fastapi import FastAPI, File, Form, HTTPException, Query, Request, UploadFile
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from .api_docs import ApiDocsManager
from .bookmarks import BookmarksManager
from .books import BookManager
from .config import load_settings
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
POSTS_DIR = _settings.posts_dir
IMG_DIR = _settings.img_dir
TOEIC_DIR = _settings.toeic_dir
BOOKS_DIR = _settings.books_dir
MUSIC_DIR = _settings.music_dir
NOTES_DIR = _settings.notes_dir
API_DOCS_DIR = _settings.api_docs_dir
BOOKMARKS_DIR = _settings.bookmarks_dir
TASKS_DIR = _settings.tasks_dir
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
# Audio served at /audio so it doesn't shadow the /music/* app routes.
app.mount("/audio", StaticFiles(directory=str(MUSIC_DIR)), name="audio")
app.mount("/toeic-audio", StaticFiles(directory=str(TOEIC_AUDIO_DIR)), name="toeic-audio")
templates = Jinja2Templates(directory=str(TEMPLATES))

# Server-side markdown rendering for the detail view (no JS needed to read).
_md = mistune.create_markdown(
    escape=False,
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
@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    features = [
        {"icon": "📝", "app": "posts",    "title": "Posts",    "href": "/posts",
         "desc": "Notes & articles with tags and full-text search.",
         "count": len(pm.list(status=None))},
        {"icon": "📚", "app": "series",   "title": "Series",   "href": "/series",
         "desc": "Multi-part topics linked in order.",
         "count": len(pm.all_series())},
        {"icon": "📖", "app": "books",    "title": "Books",    "href": "/books",
         "desc": "Collections of chapters — novels & long reads.",
         "count": len(books.collections())},
        {"icon": "🎧", "app": "toeic",    "title": "TOEIC",    "href": "/toeic",
         "desc": "Practice sets with radio answers & explanations.",
         "count": len(toeic.list())},
        {"icon": "🎵", "app": "music",    "title": "Music",    "href": "/music",
         "desc": "Imported tracks with editable metadata.",
         "count": len(music.list())},
        {"icon": "🗒️", "app": "notes",    "title": "Notes",    "href": "/notes",
         "desc": "Quick notes shown as boxes; pin your favorites.",
         "count": len(notes.list())},
        {"icon": "📄", "app": "api-docs",   "title": "API Docs",   "href": "/api-docs",
         "desc": "Document REST APIs — projects, endpoints, params, responses.",
         "count": len(api_docs.list())},
        {"icon": "🔖", "app": "bookmarks", "title": "Bookmarks", "href": "/bookmarks",
         "desc": "Saved links organised by tags and category.",
         "count": len(bmarks.list())},
        {"icon": "✅", "app": "tasks", "title": "Tasks", "href": "/tasks",
         "desc": "Task tracking with subtasks and version history.",
         "count": len(tasks_mgr.list())},
    ]
    return templates.TemplateResponse(request, "home.html", {"features": features})


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
    cover: str = Form(""),
    tags: str = Form(""),
):
    slug = books.create_collection(
        {
            "title": title,
            "author": author,
            "description": description,
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
    return templates.TemplateResponse(
        request, "book_collection.html", {"collection": collection}
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
    cover: str = Form(""),
    tags: str = Form(""),
):
    slug = books.update_collection(
        coll,
        {
            "title": title,
            "author": author,
            "description": description,
            "cover": cover,
            "tags": _parse_tags(tags),
        },
    )
    if slug is None:
        raise HTTPException(404)
    return RedirectResponse(f"/books/{slug}", status_code=303)


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
        if t:
            subtasks.append({"title": t, "status": s})
            
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
        if t:
            subtasks.append({"title": t, "status": s})
        
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
