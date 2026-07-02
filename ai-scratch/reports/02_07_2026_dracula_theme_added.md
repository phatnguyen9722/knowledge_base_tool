# Dracula Theme Added

**Date:** 02/07/2026  
**Task:** Add a new Dracula-inspired colour theme to the Knowledge Base Tool  

---

## Summary

Added a new **Dracula** theme (inspired by the popular VS Code Dracula colour scheme) to the application. The theme is selectable from the Settings panel alongside the existing seven themes (Vodka, Midnight, Sapphire, Aegean, Champagne, Rosé, Amethyst).

---

## Files Changed

### `static/style.css`

1. **Added CSS variable block** `[data-theme="dracula"]` after the Amethyst block:
   - `--bg: #282a36` — classic Dracula dark grey-blue background
   - `--fg: #f8f8f2` — soft off-white foreground
   - `--muted: #6272a4` — Dracula "comment" blue for secondary text
   - `--border: #44475a` — Dracula "current line" colour for borders
   - `--card: #1e1f29` — slightly deeper card/panel surface
   - `--accent: #bd93f9` — iconic Dracula purple accent
   - `--accent-fg: #282a36` — background colour used as text on accent elements
   - `--danger: #ff5555` — Dracula red for destructive actions
   - `--mark: #44475a` — subtle highlight/mark colour

2. **Added HTTP method badge dark overrides** so API method badges (GET, POST, PUT, PATCH, DELETE) remain legible on the dark Dracula card background.

3. **Added `.sw-dracula` swatch** — a diagonal `#282a36` / `#bd93f9` gradient for the theme picker colour preview dot.

### `templates/base.html`

- Added a **Dracula theme picker button** (with the `.sw-dracula` swatch) to the Settings → Theme panel grid, appearing after Amethyst.

### `tests/test_settings.py`

- Added `"dracula"` to the theme list in `test_settings_button_and_theme_options_render` so it asserts the picker button is rendered in the HTML.
- Added `"dracula"` to the theme list in `test_all_themes_defined_in_css` so it asserts `[data-theme="dracula"]` and `.sw-dracula` are present in the stylesheet.

---

## Colour Palette Reference

| Token        | Value     | Role                        |
|--------------|-----------|-----------------------------|
| `--bg`       | `#282a36` | Page / body background      |
| `--fg`       | `#f8f8f2` | Primary text                |
| `--muted`    | `#6272a4` | Secondary / placeholder text|
| `--border`   | `#44475a` | Borders, dividers           |
| `--card`     | `#1e1f29` | Card / panel surface        |
| `--accent`   | `#bd93f9` | Links, buttons, highlights  |
| `--accent-fg`| `#282a36` | Text on accent backgrounds  |
| `--danger`   | `#ff5555` | Errors, delete actions      |
| `--mark`     | `#44475a` | `<mark>` highlight          |

---

## No Breaking Changes

- All existing themes are untouched.
- The Dracula theme is purely additive — selecting it writes `"dracula"` to `localStorage` under the key `kb-theme`, the same mechanism used by every other theme.
