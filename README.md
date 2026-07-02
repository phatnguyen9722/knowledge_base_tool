# 📚 Knowledge Base Tool

A local-first personal knowledge base. Your notes are plain **Markdown files**
with YAML frontmatter — readable, greppable, and yours forever. The app gives
you a fast browser UI with full-text search, tag browsing, and a desktop tray
icon, with **no terminal needed** once it's running.

- **Storage:** Markdown files + SQLite FTS5 full-text index
- **Backend:** FastAPI + Uvicorn · **Frontend:** Jinja2 + marked.js
- **Desktop:** system-tray launcher (pystray) · **CLI:** Typer
- **Packaging:** PyInstaller → standalone `.app` / `.exe`

---

## What's Inside?

The Knowledge Base is split into several purpose-built mini-apps to keep your life organized. You can toggle them on or off in the **Settings**!

- **📝 Posts** — Your core notes and articles with tags and lightning-fast full-text search.
- **📚 Series** — Multi-part topics linked in chronological order.
- **📖 Books** — Collections of chapters for novels, guides, and long reads.
- **🎧 TOEIC** — Practice listening and reading sets with radio answers & explanations.
- **🎵 Music** — Your personal audio library with imported tracks and editable metadata.
- **🗒️ Notes** — Quick, colorful sticky notes. Pin your favorites to the top!
- **📄 API Docs** — Document your REST APIs (endpoints, params, and responses).
- **🔖 Bookmarks** — Saved web links organised by tags and categories.

---
## Quick start

### Option 1: Deploy and run with docker
- [Docker Document](./dockerise/README.md)

### Option 2: Manual running
#### 1. Install

Requires **Python 3.9+** (3.10+ recommended).

```bash
git clone <your-repo>  knowledge_base_tool
cd knowledge_base_tool

python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

> On Python 3.9, `python-frontmatter` is pinned to `<1.1` (1.1+ needs 3.10+).
> This is already handled in `requirements.txt`.

#### 2. Run the web app

```bash
python cli.py serve            # defaults to http://127.0.0.1:5050
# or
uvicorn app.main:app --port 5050
```

Open **http://127.0.0.1:5050** in your browser.

> **macOS note:** the default port is **5050**, not 5000 — on macOS port 5000 is
> used by the **AirPlay Receiver** (ControlCenter) and will return a `403`.
> Either keep 5050, or turn off *System Settings → General → AirDrop & Handoff →
> AirPlay Receiver* if you really want 5000.

#### 3. (Optional) Run with a tray icon

```bash
python launcher.py
```

This starts the server in the background, opens your browser, and shows a
**📚 tray icon** with *Open Knowledge Base* and *Quit*.

---

## Using the web app

### Writing posts
- Click **+ New** (or press <kbd>n</kbd>).
- The editor is **two panes**: raw Markdown on the left, **live preview** on the right.
- Fill in **title**, **category**, **tags** (comma-separated), **status**, and an
  optional **summary**, then **Save**.
- Edit any post with the **Edit** button (or <kbd>e</kbd> while viewing it).
- Delete with the **Delete** button (asks for confirmation).

### Finding posts
- **Search bar** (top): type to get **instant results** with highlighted matches.
- **Tags sidebar:** click tags to filter. Click **multiple tags** to narrow with
  **AND** logic (posts must have *all* selected tags). Click again to remove a tag,
  or **✕ clear tags**.
- **Status & Category chips:** click to filter; the URL encodes your current
  filters so you can bookmark or share a view.

### Keyboard shortcuts
| Key | Action |
|-----|--------|
| <kbd>/</kbd> | Focus the search bar |
| <kbd>n</kbd> | New post |
| <kbd>e</kbd> | Edit the post you're viewing |
| <kbd>?</kbd> | Show this shortcut help |
| <kbd>Esc</kbd> | Close search results / help |

---

## Post format

Each post is a Markdown file in `posts/` with YAML frontmatter:

```markdown
---
title: "Docker Compose Cheatsheet"   # required
created: 2024-01-15                  # required (YYYY-MM-DD)
updated: 2024-06-20                  # required (YYYY-MM-DD)
tags: [docker, devops, commands]     # required
category: DevOps                     # required
status: published                    # published | draft | archived
pinned: false                        # optional — pins to top of the feed
summary: "Short blurb on the card"   # optional
---

Your Markdown content starts here…
```

Tags are automatically lower-cased and trimmed. Pinned posts always sort to the
top of the feed; the rest are ordered by most-recently-updated. Full Unicode
(including Vietnamese) is supported in titles, tags, and content.

---

## Command-line interface

The `cli.py` Typer app works on the same data as the web app.

```bash
python cli.py --help
```

| Command | What it does |
|---------|--------------|
| `new "Title" --tags a,b --cat DevOps --status published` | Create a post (defaults to **draft**) |
| `list --status published` | List posts (📌 pinned first) |
| `search "query" --tag docker --cat DevOps` | Full-text search |
| `serve --port 5000 --reload` | Run the web app |
| `build-index` | Rebuild the tag + search indexes from disk |
| `export --out dist/site --status published` | Export a static HTML site |

**Examples**

```bash
python cli.py new "My First Note" --tags docker,ops --status published
python cli.py search docker
python cli.py export --out dist/site && open dist/site/index.html
```

### Static export
`export` produces a self-contained static site (`index.html` + one page per
post + `style.css`) with relative links — drop it on any static host or open it
straight from disk.

---

## Configuration

Edit `config.yaml` in the project root:

```yaml
server:
  host: 127.0.0.1
  port: 5050                # avoid 5000 on macOS (AirPlay Receiver)

data:
  posts_dir: posts          # where your .md files live
  attachments_dir: attachments
  tags_dir: tags
  db_path: .kb/search.db    # SQLite FTS5 index (auto-generated)

ui:
  theme: light              # light | dark
  page_size: 20             # posts per page in the feed
```

The search index in `.kb/` is rebuildable at any time with
`python cli.py build-index`, so it's safe to delete.

---

## Building a standalone app

Package the whole thing into a single executable with **no Python required** to run:

```bash
# macOS / Linux  -> dist/kb-tool
./build.sh

# Windows        -> dist\kb-tool.exe
build.bat
```

> Your `posts/` and `.kb/` directories live **next to** the executable (they are
> your data and stay outside the bundle). Use `config.yaml` to point elsewhere
> if you want your notes in a different folder.

---

## Project layout

```
knowledge_base_tool/
├── app/
│   ├── main.py          # FastAPI app + routes
│   ├── models.py        # Pydantic Post schema
│   ├── parser.py        # frontmatter ↔ Post
│   ├── post_manager.py  # CRUD + slugify + auto-index
│   ├── search.py        # SQLite FTS5 engine
│   ├── tag_manager.py   # tag counts + index.json
│   ├── exporter.py      # static HTML export
│   ├── hooks.py         # plugin event system
│   └── config.py        # settings loader
├── templates/           # Jinja2: base / list / detail / editor
├── static/              # style.css, app.js, icon.png
├── posts/               # your Markdown notes
├── tests/               # pytest suite
├── cli.py               # Typer CLI
├── launcher.py          # tray-icon desktop launcher
├── config.yaml
└── requirements.txt
```

---

## Extending with plugins (hooks)

React to post events without touching the core:

```python
from app.hooks import on

@on("on_post_created")
def notify(post):
    print(f"New post: {post.title}")

# Events: on_post_created, on_post_updated, on_post_deleted
```

Handler errors are isolated — a broken plugin can't break a save.

---

## Running the tests

```bash
python -m pytest tests/ -q
```

The suite covers the data model, parsing, CRUD + search, the web API, the
search/tag UI backend, hooks, the exporter, and the CLI.

---

## Troubleshooting

- **`No module named uvicorn` / `multipart` / `mistune`** — run
  `pip install -r requirements.txt` inside your activated virtualenv.
- **Search returns nothing after editing files by hand** — rebuild the index:
  `python cli.py build-index`.
- **`python-frontmatter` import error on Python 3.9** — make sure the pinned
  `<1.1` version installed (it's in `requirements.txt`).
- **Tray icon doesn't appear** — `launcher.py` needs a desktop session and
  `pystray` + `pillow` installed; on a headless server use `serve` instead.
