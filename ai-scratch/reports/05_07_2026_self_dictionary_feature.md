# Self Dictionary Feature Report

**Date:** 05/07/2026  
**Goal:** Create a standalone Dictionary application within the Knowledge Base to store, search, and organize vocabulary/phrases with Markdown descriptions and tags.

---

## 1. Database Architecture (`app/dictionary_db.py`)
- Created a robust, high-performance SQLite database stored independently at `.kb/dictionary.db`.
- **Schema Design:**
  - `dictionary` table: Stores the `word` and Markdown `description`.
  - `dict_tags` table: Implements a 1-to-many relationship linking a word to multiple `tags`, using `ON DELETE CASCADE` for automatic cleanup.
- **Resilience:** Implemented an automatic initialization sequence that ensures the `.kb` directory is created if missing (which fixed a Docker startup crash).

## 2. API Endpoints (`app/main.py`)
Developed a complete RESTful backend to power the dictionary:
- `GET /api/dictionary`: Fetches words. Supports complex queries, including searching within descriptions, searching specific `#tags`, and fast A-Z / Z-A sorting (`sort_dir`).
- `POST /api/dictionary`: Safely creates a new entry and its associated tags.
- `PUT /api/dictionary/{id}`: Updates existing words, automatically rebuilding the tag associations.
- `DELETE /api/dictionary/{id}`: Permanently removes an entry.

## 3. UI/UX Implementation (`templates/dictionary.html`)
- **Premium Grid Layout:** Upgraded from a standard vertical list to a dynamic CSS Grid, displaying words as beautiful cards that smoothly elevate when hovered.
- **Visual Polish:** The target words use a sleek text-gradient to stand out, and action buttons (Edit/Delete) remain hidden until hover for a clean, modern aesthetic.
- **Interactive Search:** Built a responsive, debounced search bar that updates the dictionary in real-time as you type, with pill-shaped modern UI elements.
- **Markdown Support:** The description field hooks directly into `marked.js` to render rich formatting (bold, italic, code blocks) seamlessly.
- **Add/Edit Modal:** Added an intuitive pop-up interface for quickly creating or modifying vocabulary entries.

## 4. Settings Integration (`static/app.js` & `templates/base.html`)
- Injected the Dictionary shortcut into the top navigation bar and the main `home.html` dashboard using the `📕` icon.
- Registered the Dictionary in `app.js`'s `FEATURE_LIST` and `APP_ICONS_DEFAULT` so it properly appears in the user's **Settings (⚙)** modal, allowing them to toggle its visibility or change its emoji icon like any other core app.
