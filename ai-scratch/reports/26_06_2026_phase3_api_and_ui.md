# Report — Phase 3: API & UI cơ bản

- **Date:** 2026-06-26
- **Author:** Claude (AI agent)
- **Source spec:** `requirements.md` → Execution plan, Phase 3
- **Status:** ✅ Complete — **MILESTONE reached: app usable in the browser.** All checklist items done, 25/25 tests passing, live server boots.

---

## 1. Objective

Deliver Phase 3: the FastAPI web layer and basic UI on top of the Phase 2
core — list/detail/editor pages, CRUD routes, and a JSON search endpoint. This
is the milestone phase: after it, the app is usable in a browser.

## 2. What I did

| File | Purpose |
|------|---------|
| `app/main.py` | FastAPI app: config load, mistune markdown filter, routes `/`, `/posts/{slug}`, `/new` (GET+POST), `/edit/{slug}` (GET+POST), `DELETE /posts/{slug}`, `/api/search`; pagination |
| `templates/base.html` | Shared layout: topbar (search + New), tag sidebar, theme hook |
| `templates/list.html` | Blog-style feed, pinned-first, status badges, pagination |
| `templates/detail.html` | Metadata header, server-rendered markdown, back link, edit/delete |
| `templates/editor.html` | 2-pane editor: raw markdown textarea + live preview (marked.js) |
| `static/style.css` | Full stylesheet, light + dark theme via CSS vars, responsive |
| `static/app.js` | Delete-button glue (fetch DELETE) + marked.js live preview |
| `tests/test_api.py` | 8 API smoke tests (TestClient) |

### Design decisions / deviations

- **Markdown split: server vs client.** Detail page renders markdown
  **server-side with mistune** (readable with JS off); the editor uses
  **marked.js** client-side for live preview. Matches the spec's dependency set
  (mistune>=3 + marked.js) and is more robust than the spec's purely
  browser-rendered approach.
- **Config-driven paths/port.** `main.py` loads `config.yaml` for `posts_dir`,
  `db_path`, `page_size`, and `theme` (spec hard-coded these). Falls back to
  sensible defaults if config is missing.
- **Pagination added** (`page` query param + `page_size` from config) for the
  "pagination" checklist item — the spec's list route had none.
- **`/api/search` returns highlighted snippets** (reuses Phase 2
  `search_snippets`) and excludes `content` from the payload.
- **`summary` field wired** through the create/edit forms (spec forms omitted it).
- **Deferred to Phase 4 (intentionally):** debounced live search, tag-cloud
  multi-select, keyboard shortcuts. `app.js` notes this. The search box here
  does a normal form GET to `/`.
- **`static/icon.png` not created** — it's a Phase 5 deliverable; nothing in
  Phase 3 references it.

### Fixes made during the phase (caught by test warnings)

- **`PostManager.update` now re-validates** via `Post(**{**dump, **data})`
  instead of `model_copy(update=...)`. The old path stored `status` as a raw
  string, which would break `post.status.value` in templates and emitted a
  Pydantic serialization warning.
- **Migrated to the non-deprecated `TemplateResponse(request, name, ctx)`**
  signature (Starlette deprecation).

## 3. Tests

`tests/test_api.py` (8) + Phase 2 (9) + Phase 1 (8) = **25 total**.

| API test | Covers |
|----------|--------|
| `test_empty_home_renders` | empty state |
| `test_create_redirects_and_detail_renders` | POST /new → 303, server-rendered markdown |
| `test_home_lists_created_post` | feed listing + tags |
| `test_edit_form_and_update` | GET/POST /edit/{slug} |
| `test_delete_then_404` | DELETE + subsequent 404 |
| `test_api_search_returns_snippet` | /api/search highlight + content excluded |
| `test_detail_404_for_missing` | 404 path |
| `test_new_form_renders` | editor form |

**Unit/integration result:** `25 passed in 0.31s` (no warnings).

**Live boot check** (uvicorn on :5050):

| Route | HTTP |
|-------|------|
| `GET /` | 200 |
| `GET /static/style.css` | 200 |
| `GET /new` | 200 |

## 4. Environment notes

- Installed into `.venv`: `fastapi`, `jinja2`, `mistune>=3`, `pyyaml`,
  `python-multipart` (required for form POSTs), `httpx` (TestClient), `uvicorn`.
- `python-multipart` is required by the `Form(...)` routes — already in
  `requirements.txt` transitively via FastAPI usage; ensure it's installed.
- Python 3.9.6; `python-frontmatter<1.1` pin from Phase 1 still applies.

## 5. Phase 3 checklist status

- [x] `app/main.py` – routes: GET/POST /posts, /search, /new, /edit/{slug}, DELETE
- [x] `templates/base.html` – layout, sidebar tags
- [x] `templates/list.html` – feed, pagination, pinned first
- [x] `templates/detail.html` – render markdown, metadata header, back link
- [x] `templates/editor.html` – 2-panel raw | live preview (marked.js)
- [x] `static/style.css` + `static/app.js`

## 6. How to verify

```bash
.venv/bin/pip install fastapi jinja2 "mistune>=3" pyyaml python-multipart httpx uvicorn \
    pydantic "python-frontmatter>=1.0,<1.1" python-slugify pytest
# tests
.venv/bin/python -m pytest tests/ -q
# live
.venv/bin/python -m uvicorn app.main:app --port 5000
# then open http://127.0.0.1:5000
```

## 7. Next steps (Phase 4 — Search UI & Tag browser)

- Realtime search bar: debounce 200ms, highlight matches (wire to `/api/search`)
- Tag cloud + multi-tag filter (AND logic)
- Status/category dropdown chips, URL-encoded state
- Keyboard shortcuts: `/` focus search, `n` new, `e` edit, `?` help
