# Report — Back-to-top floating button

- **Date:** 2026-06-26
- **Author:** Claude (AI agent)
- **Source:** User request — a "top" button at the bottom-right corner to jump back to the top of the page.
- **Status:** ✅ Complete — 51/51 tests passing, JS syntax-checked.

---

## 1. Objective

Add a floating button fixed at the **bottom-right corner** that appears once the
user scrolls down and smooth-scrolls the page back to the top when clicked.

## 2. What I did

| File | Change |
|------|--------|
| `templates/base.html` | Added `<button id="to-top" class="to-top" aria-label="Back to top">↑</button>` (present on every page via the shared layout). |
| `static/style.css` | `.to-top` — fixed bottom-right circular button, themed (`--accent`), drop shadow; hidden by default (`opacity/visibility`), revealed via `.to-top.visible`; smooth fade/slide transition. |
| `static/app.js` | Toggles `.visible` when `window.scrollY > 300` (passive scroll listener), and `scrollTo({ top: 0, behavior: "smooth" })` on click. |
| `tests/test_totop.py` | 3 tests: button renders; JS has scroll logic; CSS has the styles. |

### Design decisions
- **Floating FAB, not a literal footer element.** The app has no `<footer>`; a
  fixed bottom-right button is the conventional "back to top" pattern and matches
  "footer right corner". It sits at `z-index: 40` (below modals at 50).
- **Appears only after scrolling 300px** so it never clutters short pages (e.g.
  the SonarQube post that doesn't scroll).
- **Themed** via the same CSS variables, so it adapts to all six themes.
- **Accessible:** real `<button>` with `aria-label` and `title`.

## 3. Tests

`tests/test_totop.py` (3) + prior suite (48) = **51 total**.

| Test | Covers |
|------|--------|
| `test_button_renders_on_page` | `id="to-top"` + aria-label in HTML |
| `test_app_js_has_scroll_logic` | `#to-top` / `scrollTo` / `behavior` present |
| `test_css_has_to_top_styles` | `.to-top` / `.to-top.visible` / `position: fixed` |

**Result:** `51 passed in 0.53s`. `node --check static/app.js` → OK.

> The scroll/visibility interaction is browser-only; verified via render +
> JS/CSS presence checks. Manual check below.

## 4. How to verify (manual)

```bash
.venv/bin/python cli.py serve     # http://127.0.0.1:5050
# Open a long post → scroll down ~300px → a circular ↑ button fades in at the
# bottom-right → click it → the page smooth-scrolls to the top.
```

No restart needed for this one beyond the usual: it's a template + static-asset
change, and the dynamic `?v=` cache-bust means a normal reload picks it up.
(The `base.html` edit is a template, auto-reloaded by Jinja.)

## 5. Next steps / ideas

- Optional: hide the button when the TOC is open on mobile, or nudge it above
  any future footer bar.
