# Report — Post series (link posts as a series of topics)

- **Date:** 2026-06-26
- **Author:** Claude (AI agent)
- **Source:** User request — link to other posts as a series of topics.
- **Status:** ✅ Complete — 57/57 tests passing, verified live end-to-end.

---

## 1. Objective

Let posts be grouped into a named **series** so a post can link to the other
parts in order (Part 1 → Part 2 → …), with in-page navigation between them.

## 2. What I did

| File | Change |
|------|--------|
| `app/models.py` | Added `series: str = ""` and `series_order: int = 0` to the `Post` model. Optional + defaulted, so existing posts read back fine. |
| `app/post_manager.py` | `series(name)` → all posts in a series, ordered by `(series_order, created, title)`. |
| `app/main.py` | Detail route computes a `series_nav` dict (members, current, part N of M, prev, next) when the post has a series. Create/edit routes accept `series` + `series_order` form fields (parsed safely via `_to_int`). |
| `templates/editor.html` | Series name + order inputs. |
| `templates/detail.html` | A **series box** at the top of the article (list of all parts, current highlighted, "part N of M") and a **prev/next pager** at the bottom. |
| `static/style.css` | `.series-box` (accent left border, ordered list, current highlighted) and `.series-pager` (space-between prev/next). |
| `cli.py` | `new` gained `--series` and `--order`. |
| `tests/test_series.py` | 6 tests (model, manager ordering, detail rendering, form persistence). |

### Data model choice
- A series is just a **shared `series` string** across posts + a per-post
  `series_order` int. No central registry to maintain — membership is derived
  by scanning frontmatter, consistent with how tags/categories already work.
- Ordering is `series_order`, then `created`, then `title` as tie-breakers.
- A post with `series == ""` is standalone; no series UI shows.

### Design decisions
- **Series box + prev/next** rather than just "related links" — matches the
  "series of topics" framing (ordered, with a sense of progress: "part 2 of 3").
- **Server-computed prev/next** so navigation works without JS.
- Empty `series`/`0` order are written to frontmatter like the existing empty
  `summary` — consistent, harmless.

## 3. Tests

`tests/test_series.py` (6) + prior suite (51) = **57 total**.

| Test | Covers |
|------|--------|
| `test_post_series_fields_default_and_set` | model fields |
| `test_series_returns_ordered_members` | ordering + membership filter |
| `test_series_empty_name_returns_empty` | standalone case |
| `test_detail_shows_series_box_and_prev_next` | series box, "part N of M", sibling links, pager |
| `test_detail_no_series_box_when_standalone` | no UI for non-series posts |
| `test_create_via_form_persists_series` | form → persisted `series`/`series_order` |

**Result:** `57 passed in 0.54s`.

**Live check** (uvicorn :5058, 3-part "Docker Basics" series): viewing part 2
showed the series box, "part 2 of 3", links to parts 1 & 3, and the prev/next
pager. Test posts cleaned up afterward.

## 4. How to verify (manual)

```bash
.venv/bin/python cli.py serve     # http://127.0.0.1:5050
# Create/edit 2-3 posts, set the same "Series name" and ascending "Order".
# Open any of them → a "Series" box lists all parts (current highlighted) with
# ← prev / next → links at the bottom.
# Or via CLI:
.venv/bin/python cli.py new "Intro" --series "Docker Basics" --order 1 --status published
```

## 5. Next steps / ideas

- A series index page (`/series/<name>`) listing all parts, and a series badge
  on list cards.
- Auto-suggest existing series names in the editor (datalist).
