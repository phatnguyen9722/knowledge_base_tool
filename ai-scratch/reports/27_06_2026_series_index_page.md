# Report — Series index page + name sorting

- **Date:** 2026-06-27
- **Author:** Claude (AI agent)
- **Source:** User request — a "Series" button left of New that opens a page listing only series, sortable by name (A–Z, Z–A).
- **Status:** ✅ Complete — 68/68 tests passing, verified live.

---

## 1. Objective

Add a **Series** button in the topbar (left of **+ New**) linking to a page that
lists every series, with a sort control for name **A→Z / Z→A**.

## 2. What I did

| File | Change |
|------|--------|
| `app/post_manager.py` | `all_series()` → one entry per distinct series: `{name, count, first_slug, latest}` (first_slug = earliest part, the entry point; latest = newest update). Sorted A–Z. |
| `app/main.py` | `GET /series?sort=az|za` route; `az` is the default and any invalid value falls back to `az`. Z–A just reverses the A–Z list. |
| `templates/base.html` | Added `📚 Series` button immediately **left of + New**. |
| `templates/series_list.html` | New page: heading + count, A→Z / Z→A sort chips (active state), one card per series (name links to its first part, with part-count badge + last-updated). Empty-state hint. |
| `static/style.css` | `.series-sort` bar spacing. |
| `tests/test_series_index.py` | 6 tests. |

### Design decisions
- **Each series links to its first part** (`first_slug`). Opening it shows the
  existing series box (all parts + prev/next), so the index is a clean entry
  point without needing a separate per-series route.
- **Sort is server-side via `?sort=`** (URL-encoded, bookmarkable, works with JS
  off) rather than client-side JS — consistent with how the list-page facets
  already work.
- **Reuses existing card styles** so the series page matches the post feed.
- Only posts with a non-empty `series` appear; standalone posts are ignored.

## 3. Tests

`tests/test_series_index.py` (6) + prior suite (62) = **68 total**.

| Test | Covers |
|------|--------|
| `test_all_series_groups_and_counts` | grouping, count, first_slug, A–Z default |
| `test_series_button_in_topbar` | `/series` link present |
| `test_series_page_sort_az` | A→Z order + chip |
| `test_series_page_sort_za` | Z→A order |
| `test_series_page_empty_state` | "No series yet" |
| `test_series_page_bad_sort_defaults_az` | invalid sort → A–Z |

**Result:** `68 passed in 0.61s`.

**Live check** (uvicorn :5061): topbar Series button present; A–Z and Z–A both
ordered correctly. It also surfaced the user's **real existing series**
("Docker-From-Zero-To-Hero", "Python Concurrency") alongside the test data,
confirming it reads live posts. Only the seeded test posts were cleaned up; real
posts were left untouched.

## 4. How to verify (manual)

```bash
.venv/bin/python cli.py serve     # restart to pick up the new route
# Click "📚 Series" in the topbar → list of series → toggle A→Z / Z→A.
# Click a series → opens its first part (with the series box + prev/next).
```

## 5. Next steps / ideas

- Add sort by part-count or last-updated.
- A dedicated `/series/<name>` page (full description + all parts) if series
  grow large.
