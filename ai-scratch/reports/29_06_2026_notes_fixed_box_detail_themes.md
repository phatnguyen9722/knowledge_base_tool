# Report — Notes: fixed-size boxes, click-to-open, per-note themes

- **Date:** 2026-06-29
- **Author:** Claude (AI agent)
- **Source:** User request — note boxes should be a fixed size; click a box to see the full note; add a per-note theme (e.g. lines, dots, …).
- **Status:** ✅ Complete — 152/152 tests passing, verified live.

---

## 1. Objective

1. Make note boxes a **fixed size** (clamp overflowing content).
2. **Click a box → open the full note** (a detail view).
3. Add a **per-note theme** — a background style chosen per note.

## 2. What I did

| File | Change |
|------|--------|
| `app/notes.py` | `Note.theme` field + `NOTE_THEMES = ["plain","lines","dots","grid","sticky"]`; `_norm_theme` validates (unknown → `plain`). create/update/read carry the theme. |
| `app/main.py` | New `GET /notes/{slug}` detail route (renders full content via `render_with_toc`). Create/edit accept a `theme` field; editor gets the theme list. |
| `templates/notes_list.html` | Each box: `note-theme-<theme>` class + a **stretched `.note-open` link** to the detail view. |
| `templates/note_detail.html` | **New** full-note page (themed) with pin/edit/delete + back. |
| `templates/note_edit.html` | Theme `<select>`. |
| `static/style.css` | Fixed `240px` box height, content clamp with a fade mask, stretched-link click target, and the four theme background patterns + detail styling. |

### Themes
- **plain** (default), **lines** (ruled), **dots** (dotted grid), **grid**
  (graph paper), **sticky** (yellow sticky note). Patterns are drawn with CSS
  gradients using the theme's `--border` color, so they adapt to the app theme;
  `sticky` sets its own warm background + readable text.

### Design decisions
- **Fixed box + clamp:** the box is a flex column at a fixed height; the content
  area flexes and is clipped with a `mask-image` fade so the truncation looks
  clean on **any** background pattern. The date/title stay at top and the
  pin/tags/actions stay pinned at the bottom.
- **Whole-card click via a stretched link:** a `.note-open` `<a>` covers the card
  (`position:absolute; inset:0; z-index:1`); the pin button, tag chips, and
  edit/delete sit above it (`z-index:2`) so they remain independently clickable.
  No JS needed.
- **Detail route ordering:** `GET /notes/{slug}` is registered **after**
  `/notes/new` so "new" isn't captured as a slug (covered by a test).

> Note on "carou": I couldn't map that to a known pattern, so I shipped
> plain/lines/dots/grid/sticky. Adding another named theme is a one-liner
> (`NOTE_THEMES` + a `.note-theme-<name>` CSS rule) — tell me what "carou"
> should look like and I'll add it.

## 3. Tests

`tests/test_notes_theme.py` (8) + prior suite (144) = **152 total**.

| Area | Tests |
|------|-------|
| Manager | theme defaults to plain; persists; invalid → plain; all `NOTE_THEMES` accepted |
| Routes | editor theme select; box gets theme class + open link; detail renders full markdown + theme; 404; `/notes/new` not shadowed |
| CSS | fixed `240px` height, `.note-open`, all theme classes present |

**Result:** `152 passed in 1.02s`.

**Live check** (uvicorn :5072): a long "Dotted Memo" note → box showed
`note-theme-dots` + an open-link to `/notes/dotted-memo`; the detail page
rendered the full markdown with the theme; editor showed the theme select.
Test note cleaned up.

## 4. How to verify (manual)

```bash
.venv/bin/python cli.py serve     # restart for the detail route
# 🗒️ Notes → New Note → pick a Theme (Lines/Dots/Grid/Sticky) → Save.
# Boxes are uniform height with content clamped; click any box to read the
# full note on its own themed page.
```

## 5. Next steps / ideas

- More themes / per-note accent color.
- "Read more" affordance text on hover; masonry layout for varied content.
