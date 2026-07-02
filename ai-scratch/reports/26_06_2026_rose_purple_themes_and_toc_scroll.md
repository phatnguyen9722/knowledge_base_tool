# Report — Rose & Purple themes + TOC behavior + asset cache-busting

- **Date:** 2026-06-26
- **Author:** Claude (AI agent)
- **Source:** Several user requests — (1) add Rose & Purple themes; (2) change TOC scroll behavior; (3) follow-up debugging of "TOC won't move".
- **Status:** ✅ Complete — 48/48 tests passing. Final TOC behavior: **sticky follow-along** (per user's confirmed choice).

---

## 1. Objective

1. Extend the theme picker with two new colors: **Rose** and **Purple**.
2. Get the detail-page Table of Contents behaving the way the user wants while
   scrolling.
3. Fix the underlying reason CSS/JS edits weren't showing up (browser caching).

## 2. What I did

### Themes (Rose + Purple)
| File | Change |
|------|--------|
| `templates/base.html` | Added **Rose** and **Purple** options (swatch + label) to Settings → Theme. |
| `static/style.css` | `[data-theme="rose"]` (light, crimson accent `#e11d48`) and `[data-theme="purple"]` (deep violet dark, accent `#a855f7`); `.sw-rose` / `.sw-purple` swatches. |
| `tests/test_settings.py` | Extended assertions to all six themes + swatches. |

Picker now offers six themes: Light, Dark, Ocean, Clay, Rose, Purple. No JS
change needed — theme switching/persistence handles any `data-theme-set` value.

### TOC behavior (the journey)
The request "make the TOC move, not pinned at top" was ambiguous and went
through two iterations:

1. First I read it as **scroll-away** → changed `.toc` from `position: sticky`
   to static.
2. User reported it still didn't move. Diagnosed against their **live** server:
   the served CSS had no sticky and the DOM was correct — the real cause was that
   the test post ("SonarQube") is only **~90 words**, so the page doesn't scroll
   at all; nothing moves because there's nothing to scroll.
3. Clarified with the user: they actually want **follow-along (sticky)** — the
   Contents stays visible while scrolling a long post.

**Final** (`static/style.css`):
```css
.toc {
  position: sticky;
  top: 70px;                       /* clear the sticky top bar */
  max-height: calc(100vh - 90px);  /* long TOCs scroll internally, never overflow */
  overflow-y: auto;
  font-size: .9rem;
}
```
This is better than the original sticky (which lacked `max-height`/`overflow`):
a very long TOC now scrolls within itself instead of running off-screen.

### Asset cache-busting (root cause of "edits don't show up")
The earlier symptom — CSS changes not appearing — was browser caching of
`/static/style.css`. Fixed in two steps:
| File | Change |
|------|--------|
| `app/main.py` | `_asset_version()` returns `max(mtime)` of `style.css`/`app.js`. Registered as a **callable** Jinja global so it's re-evaluated on every render. |
| `templates/base.html` | `style.css?v={{ asset_v() }}` and `app.js?v={{ asset_v() }}`. |

Because the version is the file mtime computed per request, any asset edit
changes the `?v=` automatically — **no server restart needed** for future
CSS/JS tweaks. (Python/template changes still require a restart, as always.)

## 3. Tests

`test_settings.py` updated for six themes; full suite green.

**Result:** `48 passed in 0.51s` (Python 3.9.6).

**Verified against a fresh server:**
- Served CSS contains the sticky `.toc` block (top/max-height/overflow).
- Asset version updated on its own across edits (`1782458777` → `1782460018`),
  confirming dynamic cache-busting.
- Diagnosed the live SonarQube post body at ~90 words / 481 chars — too short to
  scroll, which explained the "TOC won't move" report.

> Note: the visual scroll behavior is browser-only; verified via served-CSS
> inspection + the content-length diagnosis rather than a pixel test.

## 4. Operational note

Applying this batch required **one server restart** (Python + template changes).
After that restart, the dynamic `?v=` means static-asset edits no longer need a
restart — just a normal reload.

## 5. How to verify (manual)

```bash
# restart once to pick up main.py/base.html changes:
.venv/bin/python cli.py serve     # http://127.0.0.1:5050
# Themes: ⚙ Settings → try Rose / Purple (persists across reloads).
# TOC: open a long post (or shrink the window) → Contents stays alongside as you
#      scroll; on a short post it sits still because the page doesn't scroll.
```

## 6. Lesson logged

"Move / not pinned" was genuinely ambiguous (scroll-away vs. follow-along). When
a UI-behavior request can mean two opposite things, confirm with the user before
implementing — and check whether the test content is even long enough to exhibit
the behavior being debugged.
