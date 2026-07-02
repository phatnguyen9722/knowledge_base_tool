# Report — Phase 2: PostManager & Search Core

- **Date:** 2026-06-26
- **Author:** Claude (AI agent)
- **Source spec:** `requirements.md` → Execution plan, Phase 2
- **Status:** ✅ Complete — all Phase 2 checklist items done, 17/17 tests passing (9 new + 8 from Phase 1)

---

## 1. Objective

Deliver Phase 2: the persistence and search core — CRUD over markdown posts,
SQLite FTS5 full-text search with auto-indexing on save, and tag aggregation
with a persisted index. Spec deliverable: "CRUD, FTS5, TagManager".

## 2. What I did

| File | Purpose |
|------|---------|
| `app/search.py` | `SearchEngine` — FTS5 virtual table; `index` / `remove` / `rebuild` / `search` / `search_snippets` (highlighted) / `close` |
| `app/post_manager.py` | `PostManager` — `create` / `read` / `update` / `delete` / `list` / `rebuild_index`, unicode slugify with collision handling, FTS5 auto-index on every write |
| `app/tag_manager.py` | `TagManager` — `all_tags()` (counts) + `rebuild()` → `tags/index.json` |
| `tests/test_integration.py` | 9 integration tests |

### Design decisions / deviations

- **Reused `app/parser.py` (Phase 1)** for read/write instead of duplicating
  frontmatter logic. The spec's `PostManager` had its own inline `_write`/`read`;
  delegating to `parse_post` / `dump_post` keeps one source of truth for
  serialization and UTF-8 handling.
- **Slug collision handling added.** Spec slugifies the title directly, which
  would silently overwrite an existing post with the same title. `_unique_slug`
  appends `-2`, `-3`, … on collision.
- **`search_snippets()` added** for the "highlight snippet" checklist item,
  using FTS5's `snippet()` with `<mark>…</mark>` wrapping. Plain `search()`
  (slug list) is kept for the simple ranked case.
- **`list()` sort simplified** to two stable sorts (newest-updated, then pinned
  on top) — clearer and correct vs. the spec's single mixed-direction key
  (dates can't be negated in a tuple key).
- **`create()` defaults `created`/`updated` to today** if not supplied, so the
  CLI/API callers don't have to.
- **Empty-query guard** in `search()`/`search_snippets()` returns `[]` rather
  than passing an empty MATCH to FTS5.

## 3. Tests

`tests/test_integration.py` (9) + `tests/test_models.py` (8 from Phase 1):

| Test | Checklist case |
|------|----------------|
| `test_create_then_read_round_trip` | CRUD round-trip |
| `test_update_persists_and_reindexes` | CRUD + search consistency |
| `test_delete_removes_file_and_index` | CRUD + index cleanup |
| `test_slug_collision_disambiguates` | slugify robustness |
| `test_list_pinned_first_then_newest` | list ordering |
| `test_search_recall_by_content_and_tag` | search recall |
| `test_search_snippet_highlights_match` | highlight snippet |
| `test_utf8_vietnamese_round_trip_and_search` | UTF-8 tiếng Việt |
| `test_tag_manager_counts_and_persists` | TagManager + index.json |

**Result:** `17 passed in 0.15s` (Python 3.9.6, pytest 8.4.2, in `.venv/`).

## 4. Environment notes

- Added **`python-slugify`** to the venv (already in `requirements.txt`).
- FTS5 ships with the stdlib `sqlite3` on this machine — no extra dependency.
- Python 3.9.6 + `python-frontmatter<1.1` pin from Phase 1 still applies.

## 5. Phase 2 checklist status

- [x] `app/post_manager.py` – create / read / update / delete / list / slugify
- [x] `app/search.py` – SQLite FTS5, auto-index on save, highlight snippet
- [x] `app/tag_manager.py` – build index.json, all_tags(), rebuild()
- [x] Integration tests: CRUD round-trip, search recall, UTF-8

## 6. How to verify

```bash
.venv/bin/pip install pydantic "python-frontmatter>=1.0,<1.1" pyyaml python-slugify pytest
.venv/bin/python -m pytest tests/ -v
```

## 7. Next steps (Phase 3 — API & UI cơ bản)

- `app/main.py` — FastAPI routes: GET/POST `/posts`, `/search`, `/new`, `/edit/{slug}`, DELETE
- `templates/` — `base.html`, `list.html`, `detail.html`, `editor.html`
- `static/style.css` + `static/app.js` (marked.js live preview, search glue)
- Milestone after Phase 3: app usable in the browser.
