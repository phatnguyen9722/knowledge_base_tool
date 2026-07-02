# Report — Move TOC to the right

- **Date:** 2026-06-26
- **Author:** Claude (AI agent)
- **Source:** User request — move the Table of Contents to the right.
- **Status:** ✅ Complete — 45/45 tests passing, verified live.

---

## 1. Objective

Move the post Table of Contents from the left sidebar to a right-hand rail on
the detail page, without leaving an empty left column.

## 2. What I did

| File | Change |
|------|--------|
| `templates/detail.html` | Removed the `{% block sidebar %}` TOC; wrapped the article + TOC in `.detail-wrap`, with the TOC as a trailing `<aside class="toc-rail">` (renders to the **right** of the article). |
| `templates/base.html` | Collapsed the sidebar markup to one line so an unused sidebar block produces a **truly empty** `<aside class="sidebar"></aside>`. |
| `static/style.css` | `.sidebar:empty { display: none; }` (reclaims the left column on detail/editor pages); `.detail-wrap` flex layout (`article` flex:1, `.toc-rail` 220px on the right); mobile: `column-reverse` so the TOC sits above the article, with a non-sticky static TOC. |

### Design decisions
- **TOC as a right rail inside the content** rather than flipping the global
  layout — keeps the shared left sidebar semantics intact for the list page.
- **`.sidebar:empty` collapse** is the key trick: the detail page no longer
  overrides the sidebar block, so it's empty and disappears, giving the article
  the full width with the TOC on the right. Bonus: the editor page (also an
  empty sidebar) now uses full width too.
- **Mobile:** `column-reverse` puts the TOC on top as a jump-nav (a TOC below
  the content would be useless), and the TOC un-stickies.

## 3. Tests

No test changes needed — the existing TOC assertions are class/anchor based
(`class="toc"`, `href="#..."`), which still hold in the new position.

**Result:** `45 passed in 0.42s`.

**Live check** (uvicorn :5054, post with headings A/B/C):
`class="detail-wrap"`, `class="toc-rail"`, `href="#a|#b|#c"` all present, and the
left sidebar renders as empty `<aside class="sidebar"></aside>` (collapsed by
`:empty`). Test post cleaned up afterward.

## 4. How to verify (manual)

```bash
.venv/bin/python cli.py serve     # http://127.0.0.1:5050
# Open a post with 2+ headings → "Contents" now appears on the RIGHT,
# article fills the left; narrow the window → TOC moves above the article.
```
