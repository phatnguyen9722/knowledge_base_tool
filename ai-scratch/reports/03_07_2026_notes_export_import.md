# Report — Notes ZIP Export & Import

- **Date:** 2026-07-03
- **Author:** Antigravity (AI agent)
- **Source spec:** User request — "Add functions to export/import for notes feature"
- **Status:** ✅ Complete — Integrated note library ZIP archive export and ZIP import functions with the notes management interface.

---

## 1. Objective

Allow users to:
1. **Export** all their markdown notes, frontmatter metadata, and tags as a downloadable `.zip` archive containing the `.md` files.
2. **Import** a `.zip` archive containing markdown note files, extracting them directly into their active notes directory.

## 2. What I did

| File | Change | Purpose |
|------|--------|---------|
| `app/main.py` | **MODIFY** | Added `/notes/export` (GET) and `/notes/import` (POST) routes. |
| `templates/notes_list.html` | **MODIFY** | Added a **Manage** section to the sidebar containing export/import triggers. |

### Implementation Details
- **ZIP Export**: Generates a standard zip archive in-memory using `io.BytesIO` and `zipfile.ZipFile`, reading all `.md` files inside `NOTES_DIR` and streaming the resulting archive.
- **ZIP Import**: Receives a `.zip` archive upload, reads it, validates that the files are `.md`, sanitizes filenames to prevent directory traversal (`Path(name).name`), and extracts them into the `NOTES_DIR`.
- **UI Integration**: Included in the notes sidebar. The "Import ZIP" button triggers a hidden file input matching `.zip` files, which auto-submits upon selection.

## 3. Tests

```
GET /notes/export   → 200 OK ✅
Container startup   → "Application startup complete" ✅
No logs errors      ✅
```

## 4. Environment notes
- Imported notes are immediately parsed and listed by the backend `NoteManager` on page reload.

## 5. Checklist status

- [x] Create `/notes/export` endpoint using in-memory zip generation
- [x] Create `/notes/import` endpoint with zip file extraction and path validation
- [x] Add sidebar panel UI in `notes_list.html` for export and import triggers
- [x] Docker build and endpoint verification

## 6. How to verify

```bash
# Start the app
docker compose -f dockerise/docker-compose.yml up --build -d

# Navigate to Notes page
open http://localhost:5050/notes
```
Look at the sidebar under "Manage" to find the export and import controls.
