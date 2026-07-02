# Report — Phase 4: Search UI & Tag Browser

- **Date:** 2026-06-26
- **Author:** Claude (AI agent)
- **Source spec:** `requirements.md` → Execution plan, Phase 4
- **Status:** ✅ Complete — all checklist items done, 31/31 tests passing, live behavior verified.

---

## 1. Objective

Deliver Phase 4: the search/browse polish layer on top of the working Phase 3
app — realtime search, multi-tag AND filtering, status/category facets with
URL-encoded state, and keyboard shortcuts.

## 2. What I did

### Backend
| File | Change |
|------|--------|
| `app/search.py` | New `_filters()` helper; `search()` / `search_snippets()` now accept `tags: list[str]` and combine them with **AND** logic (post must carry all tags). `tag` kept for back-compat. |
| `app/post_manager.py` | Added `categories()` → `{category: count}` (cheap frontmatter scan) for the category facet. |
| `app/main.py` | List route accepts repeated `tag` query params + `category`; applies multi-tag AND for both search and browse. Precomputes **facets with toggle URLs**: `tag_cloud`, `cat_chips`, `status_chips`, plus `prev_url`/`next_url`/`clear_url`. New `_build_url()` produces URL-encoded state. `/api/search` accepts multiple tags + category. |

### Frontend
| File | Change |
|------|--------|
| `templates/base.html` | Live-search results dropdown, `{% block sidebar %}`, keyboard-shortcuts help modal, `?` help button |
| `templates/list.html` | Sidebar facets: status chips, category chips, multi-select **tag cloud** (font-size scales with count); active-tag highlighting; AND indicator; pager uses precomputed URLs |
| `static/app.js` | **Debounced (200ms) live search** → `/api/search`, filter-aware (reads active tag/category from URL), renders `<mark>` snippets; **keyboard shortcuts** `/` `n` `e` `?` `Esc`; help modal toggle; XSS-safe title escaping |
| `static/style.css` | Styles for search dropdown, chips, tag cloud, help modal + `kbd` |

### Design decisions / deviations
- **Multi-tag via repeated `?tag=` params** (not comma-joined) — clean
  URL-encoded state and toggling, matches "URL-encoded state" requirement.
- **Facet toggle URLs computed server-side** (Python `_build_url`) rather than
  in JS, so the browse experience works without JavaScript; JS only enhances
  the live-search dropdown.
- **Snippet HTML from FTS5 is injected as-is** (it contains trusted `<mark>`
  tags); the post **title** is HTML-escaped in JS to avoid XSS from titles.
- **Tag `LIKE '%tag%'`** matching is substring-based (inherited from the spec's
  search). Acceptable for a local single-user tool; noted as a future
  sharpening if tag prefixes ever collide.

## 3. Tests

`tests/test_phase4.py` (6 new) + Phase 3 (8) + Phase 2 (9) + Phase 1 (8) = **31 total**.

| Phase 4 test | Covers |
|--------------|--------|
| `test_search_engine_multi_tag_and` | AND logic in SearchEngine |
| `test_search_engine_category_filter` | category filter in SearchEngine |
| `test_list_route_multi_tag_and` | browse AND + "all tags (AND)" indicator |
| `test_list_route_category_filter` | category browse + active chip |
| `test_list_route_renders_facets` | tag cloud + chips render |
| `test_api_search_multi_tag_and` | `/api/search` honours multiple tags |

**Result:** `31 passed in 0.36s` (Python 3.9.6).

**Live verification** (uvicorn :5051, seeded 2 posts):

| Action | Result |
|--------|--------|
| `/?tag=docker&tag=devops` | only the post with **both** tags |
| `/?category=Ops` | only the Ops post |
| `/api/search?q=compose&tag=devops` | 1 hit with `<mark>compose</mark>` snippet |

(Live-boot test posts were written to `posts/` and then **cleaned up**; the data
dirs are back to empty.)

## 4. Environment notes

- No new dependencies. marked.js still loaded from CDN in the editor only.
- Python 3.9.6; pins from earlier phases unchanged.

## 5. Phase 4 checklist status

- [x] Realtime search bar – debounce 200ms, highlight matches
- [x] Tag cloud + multi-tag filter (AND logic)
- [x] Status / category dropdown chips, URL-encoded state
- [x] Keyboard shortcuts: `/` focus search, `n` new, `e` edit, `?` help

## 6. How to verify

```bash
.venv/bin/python -m pytest tests/ -q
.venv/bin/python -m uvicorn app.main:app --port 5000
# open http://127.0.0.1:5000 — try the search box, click tags to AND-filter,
# press ? for the shortcut help.
```

## 7. Next steps (Phase 5 — Launcher, CLI & Build)

- `launcher.py` — pystray + webbrowser + uvicorn thread
- `static/icon.png` — 64×64 tray icon
- `cli.py` — Typer: new / list / search / serve / build-index
- `app/exporter.py` — static HTML export
- PyInstaller build script (macOS + Windows); `app/hooks.py` plugin events
- Test bundle on a machine without Python
