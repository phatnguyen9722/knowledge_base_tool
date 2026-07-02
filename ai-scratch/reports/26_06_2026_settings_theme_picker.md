# Report — Settings button + Theme picker (Light/Dark/Ocean/Clay)

- **Date:** 2026-06-26
- **Author:** Claude (AI agent)
- **Source:** User request — add a Settings button whose first feature is a theme
  picker with Light / Dark / Ocean + a Claude-desktop-like color.
- **Status:** ✅ Complete — 38/38 tests passing, verified live.

---

## 1. Objective

Add a **Settings** entry point to the UI and ship its first feature: a **theme
picker** offering four themes — **Light, Dark, Ocean**, and **Clay** (a warm
cream + terracotta palette in the spirit of Claude desktop). Selection persists
and applies without a flash on reload.

## 2. What I did

| File | Change |
|------|--------|
| `templates/base.html` | Added a **⚙ Settings button** in the topbar, a **Settings modal** with a Theme section (4 options + color swatches), and a `<head>` inline script that applies the saved theme **before first paint** (no FOUC). |
| `static/style.css` | New `[data-theme="ocean"]` and `[data-theme="clay"]` variable blocks (also rounded out `--accent-fg`/`--danger` for dark); `.theme-grid`, `.theme-opt`, and `.swatch` styles with per-theme preview swatches. |
| `static/app.js` | Settings modal open/close (button, close, `Esc`); theme apply → sets `data-theme`, saves to `localStorage["kb-theme"]`, marks the active option; initializes active state on load. |
| `tests/test_settings.py` | 2 tests: settings/theme markup renders; all four themes + swatches defined in CSS. |

### Theme palettes
- **Light** — white bg, blue accent (`#2563eb`) — unchanged default.
- **Dark** — near-black bg, blue accent (`#3b82f6`) — unchanged, tidied vars.
- **Ocean** — deep navy/teal (`bg #0b1f2a`, accent `#14b8a6`).
- **Clay** — warm cream (`bg #f4f0e6`, fg `#3d3929`, accent terracotta `#c15f3c`),
  the Claude-desktop-style option.

### Design decisions
- **Persistence via `localStorage`** (per browser), not `config.yaml`. It's
  instant, needs no backend round-trip, works offline, and matches how a desktop
  app remembers a personal preference. `config.yaml`'s `theme` remains the
  **default/fallback** when nothing is stored.
- **No-flash load:** a tiny inline script in `<head>` sets `data-theme` from
  `localStorage` before the body renders, so there's no light→theme flicker.
- **Extensible modal:** the Settings modal is structured as `<section
  class="setting">` blocks, so future settings (e.g. page size, font) slot in
  without restructuring.

## 3. Tests

`tests/test_settings.py` (2) + prior suite (36) = **38 total**.

| Test | Covers |
|------|--------|
| `test_settings_button_and_theme_options_render` | ⚙ button, modal, all 4 `data-theme-set` options, no-flash loader present |
| `test_all_four_themes_defined_in_css` | `[data-theme=ocean|clay|dark]` + `.sw-*` swatches in CSS |

**Result:** `38 passed in 0.50s`.

**Live check** (uvicorn :5052):
- Home page contains `id="settings-btn"` and all four `data-theme-set` options. ✓
- `/static/style.css` serves and contains the `ocean` + `clay` theme blocks. ✓

## 4. Environment notes

- No new dependencies. Pure template/CSS/JS change.
- Theme is per-browser; clearing site data resets to the `config.yaml` default.

## 5. How to verify (manual)

```bash
.venv/bin/python -m pytest tests/ -q
.venv/bin/python cli.py serve            # http://127.0.0.1:5050
# Click ⚙ → pick Ocean or Clay → reload: the theme persists with no flash.
```

## 6. Next steps / ideas

- Add more settings to the modal (page size, default status filter, font size).
- Optionally add a `?`-style keyboard shortcut to open Settings.
- If cross-device sync is ever wanted, add a `POST /api/settings` that writes
  `theme` back to `config.yaml`.
