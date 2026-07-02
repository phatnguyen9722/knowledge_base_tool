# Report — Table of Contents (TOC) feature

- **Date:** 2026-06-26
- **Author:** Claude (AI agent)
- **Source:** User request — add a Table of Contents feature.
- **Status:** ✅ Complete — 45/45 tests passing, verified live.

---

## 1. Objective

Generate a Table of Contents from each post's headings and show it on the detail
page, with clickable links that jump to the matching heading.

## 2. What I did

| File | Change |
|------|--------|
| `app/markdown.py` | **New** module. `render_with_toc(text) -> (html, toc)`: a custom mistune `HTMLRenderer` subclass injects a unique `id` on every heading and collects a flat ordered `toc` list of `{level, text, id}` for h1–h3. A fresh renderer is built per call (no shared state across requests). |
| `app/main.py` | Detail route renders via `render_with_toc()` and passes `content_html` + `toc` to the template. |
| `templates/detail.html` | Renders the body from `content_html`; adds a **Contents** `<nav class="toc">` in the sidebar (only when ≥2 TOC headings). |
| `static/style.css` | Sticky TOC styling, indentation per heading level (`toc-l1/2/3`), `scroll-behavior: smooth`, and `scroll-margin-top` so anchored headings clear the sticky topbar. |
| `tests/test_toc.py` | 7 tests (unit + detail-page integration). |
| `tests/test_api.py` | Updated one Phase 3 assertion (`<h1>Heading</h1>` → `<h1 id="heading">Heading</h1>`) to match the new anchored output. |

### Design decisions
- **Custom renderer over post-processing.** Adding ids + collecting the TOC in
  a single mistune pass is robust to inline formatting in headings (e.g.
  `# Hello *world*`), which a regex over rendered HTML would mishandle.
- **Anchors via `slugify(..., allow_unicode=True)`** (already a dependency), so
  Vietnamese headings get valid, readable anchors. Duplicate headings are
  de-duplicated (`setup`, `setup-2`, …).
- **TOC depth capped at h3** (`TOC_MAX_LEVEL = 3`) to keep the list readable;
  deeper headings still get ids (so they remain linkable) but aren't listed.
- **Shown only when ≥2 headings** — a TOC for a single heading is noise.
- **Placed in the detail-page sidebar** (previously empty on detail pages),
  sticky so it stays visible while scrolling. No layout change for list pages.
- The old `markdown` Jinja filter is now unused by the detail page but left
  registered (harmless; the exporter has its own renderer).

## 3. Tests

`tests/test_toc.py` (7) + prior suite (38, one assertion updated) = **45 total**.

| Test | Covers |
|------|--------|
| `test_headings_get_ids_and_toc_collected` | ids injected + toc list shape |
| `test_duplicate_headings_get_unique_anchors` | `setup` / `setup-2` |
| `test_deep_headings_are_anchored_but_excluded_from_toc` | h4 linkable, not listed |
| `test_toc_label_strips_inline_formatting` | `Hello *world*` → label "Hello world" |
| `test_toc_unicode_heading` | Vietnamese anchor |
| `test_detail_renders_toc_when_multiple_headings` | nav + `#anchors` on page |
| `test_detail_no_toc_for_single_heading` | TOC hidden for 1 heading |

**Result:** `45 passed in 0.42s`.

**Live check** (uvicorn :5053, post with Overview/Installation/Usage/Tips):
`class="toc"`, `href="#overview"`, `href="#installation"`, `href="#tips"`, and
`<h2 id="installation">` all present. Test post cleaned up afterward.

## 4. Environment notes

- No new dependencies (mistune 3.3.2 + python-slugify already present).

## 5. How to verify (manual)

```bash
.venv/bin/python -m pytest tests/test_toc.py -q
.venv/bin/python cli.py serve     # http://127.0.0.1:5050
# Open a post with 2+ headings → "Contents" appears in the left sidebar;
# clicking an entry smooth-scrolls to that heading.
```

## 6. Next steps / ideas

- Scroll-spy: highlight the current section in the TOC as you scroll (JS).
- Optional "collapse TOC" toggle for very long posts.
- A live TOC in the editor preview pane (currently TOC is detail-page only).
