# Font Manager Feature Report

**Date:** 05/07/2026  
**Goal:** Implement a comprehensive Font Manager to allow users to customize the application's typography with built-in fonts or their own custom font files.

---

## 1. Backend Architecture (`app/main.py`)
- **Storage:** Configured a new directory `FONTS_DIR` (`kb-data/data/fonts`) and mounted it to `/uploads/fonts/` so uploaded fonts are served statically and persist across Docker container restarts.
- **APIs:** 
  - `POST /api/fonts`: Accepts `.ttf`, `.otf`, `.woff`, and `.woff2` files (up to 10 MB). Hashes the file to prevent duplicates and saves it to the `FONTS_DIR`.
  - `GET /api/fonts`: Scans the directory and returns a JSON list of all available custom fonts.
  - `DELETE /api/fonts/{filename}`: Securely deletes an uploaded font file.
- **Bugfix:** Corrected a `NameError` where the settings object was referenced as `settings` instead of the global `_settings` during the `FONTS_DIR` initialization.

## 2. Default Fonts (`static/fonts/`)
- Downloaded three highly legible, open-source Google Fonts in the highly compressed `.woff2` and `.ttf` formats directly into the `static/fonts` folder.
- **Included Fonts:**
  - **Inter:** A clean, modern typeface designed for UI interfaces.
  - **Roboto:** Google's classic sans-serif font.
  - **Open Sans:** Excellent for long-form reading and markdown documents.

## 3. Frontend & Styling
### CSS Changes (`static/style.css`)
- Replaced the hardcoded system font on the `body` tag with a dynamic CSS variable: `var(--kb-font-family)`.
- If the variable is not set, it gracefully falls back to the system defaults (`-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif`).

### Dynamic Injection (`templates/base.html`)
- Added a `<style id="kb-font-style">` block in the document `<head>`.
- Modified the critical early-load inline JavaScript to read `kb-font` from `localStorage`. If a font is selected, it dynamically injects an `@font-face` rule and updates `--kb-font-family` **before** the browser paints the screen. This completely eliminates any "flash of unstyled text" (FOUT) on page reloads.

### Settings Interface (`static/app.js` & `templates/base.html`)
- Added a **Typography** tab to the Settings sidebar.
- Created `buildFontPanel()` to render three sections:
  1. A "System Default" reset button.
  2. A list of the built-in fonts (Inter, Roboto, Open Sans).
  3. A list of any custom fonts uploaded by the user, complete with a delete button.
- Added upload logic using JavaScript's `FormData` and `fetch` to send font files to the new `POST /api/fonts` endpoint without reloading the page. When a font is clicked, it instantly updates the UI in real-time.
