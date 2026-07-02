# Report — Phase 1: Scaffold & Data Model

- **Date:** 2026-06-26
- **Author:** Claude (AI agent)
- **Source spec:** `requirements.md` → Execution plan, Phase 1
- **Status:** ✅ Complete — all Phase 1 checklist items done, 8/8 unit tests passing

---

## 1. Objective

Deliver Phase 1 of the Knowledge Base Tool: project scaffold plus the data
model layer. Per the spec, the deliverable is "Post schema, parser, unit tests".

## 2. What I did

### 2.1 Directory structure
Created the project skeleton from the spec's "Cấu trúc thư mục":

```
posts/  attachments/  tags/  .kb/  static/  templates/  app/  tests/
ai-scratch/reports/
```

`.gitkeep` files added to `posts/`, `attachments/`, `tags/` so the empty data
directories are tracked.

### 2.2 Files created

| File | Purpose |
|------|---------|
| `app/__init__.py` | Package marker + `__version__ = "0.1.0"` |
| `app/models.py` | `PostStatus` enum + `Post` Pydantic model with `normalize_tags` validator |
| `app/parser.py` | Frontmatter parse/validate/dump helpers + `PostParseError` |
| `config.yaml` | Skeleton config: server host/port, data dirs, db path, UI theme/page_size |
| `requirements.txt` | Full dependency list from spec + `pytest` for dev |
| `.gitignore` | `.kb/ __pycache__ dist/ build/ *.spec *.pyc` + venv/OS/pytest entries |
| `tests/__init__.py` | Test package marker |
| `tests/test_models.py` | 8 unit tests |

### 2.3 Design decisions / deviations from spec

- **`app/parser.py` added** (not named explicitly in the spec). The Phase 1
  checklist requires a "Frontmatter parser + validation" but the only parsing
  code shown lives inside `PostManager` (a Phase 2 deliverable). I extracted the
  frontmatter↔Pydantic bridge into a standalone module so Phase 1 has a testable
  unit and Phase 2's `PostManager` can build on it.
- **`normalize_tags` hardened** beyond the spec snippet to also drop empty/
  whitespace-only tags, not just lower-case/strip.
- **`from __future__ import annotations`** used in `models.py`/`parser.py` so the
  `list[str]` / `str | Path` type hints work on the local Python 3.9.6.
- **`dump_post()`** added to `parser.py` to support round-trip testing now and
  `PostManager._write` later. It excludes `slug` and `content` from frontmatter
  (slug = filename, content = body), matching the spec's `_write`.

## 3. Tests

`tests/test_models.py` covers the four checklist cases plus round-trip:

| Test | Checklist case |
|------|----------------|
| `test_valid_post` | valid post |
| `test_tags_normalization_handles_none_and_empties` | tag normalization |
| `test_missing_required_field` | missing field |
| `test_wrong_type_status`, `test_wrong_type_date` | wrong type |
| `test_parse_string_valid_utf8` | UTF-8 tiếng Việt |
| `test_parse_string_missing_field_raises` | parser validation |
| `test_dump_round_trip_preserves_utf8` | round-trip integrity |

**Result:** `8 passed in 0.07s` (Python 3.9.6, pytest 8.4.2, in `.venv/`).

## 4. Environment notes

- Local interpreter is **Python 3.9.6**.
- **`python-frontmatter` 1.1+ requires Python 3.10+** (imports `typing.TypeGuard`).
  Pinned to `>=1.0,<1.1` in `requirements.txt` with an inline comment. If the
  project standardizes on Python 3.10+, this pin can be relaxed.

## 5. Phase 1 checklist status

- [x] Khởi tạo cấu trúc thư mục (posts/ attachments/ tags/ .kb/ static/ templates/)
- [x] `app/models.py` – Pydantic Post schema với validator
- [x] `app/__init__.py`, `config.yaml` skeleton
- [x] Frontmatter parser + validation (python-frontmatter + Pydantic) → `app/parser.py`
- [x] Unit tests: valid post / missing field / wrong type / UTF-8 tiếng Việt
- [x] `.gitignore`: `.kb/ __pycache__ dist/ build/ *.spec *.pyc`

## 6. How to verify

```bash
python3 -m venv .venv
.venv/bin/pip install pydantic "python-frontmatter>=1.0,<1.1" pyyaml pytest
.venv/bin/python -m pytest tests/ -v
```

## 7. Next steps (Phase 2 — PostManager & Search core)

- `app/post_manager.py` — create/read/update/delete/list/slugify (reuse `parser.py`)
- `app/search.py` — SQLite FTS5, auto-index on save, highlight snippet
- `app/tag_manager.py` — build `tags/index.json`, `all_tags()`, `rebuild()`
- Integration tests: CRUD round-trip, search recall, UTF-8
