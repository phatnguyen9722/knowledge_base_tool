# Knowledge Base Tool — Feature Reference Guide

This project is a multi-feature web application for managing personal knowledge, files, documentation, training, and utilities.

## Getting Started

To build and run the application locally inside Docker:
```bash
docker compose -f dockerise/docker-compose.yml up --build -d
```
The app will be accessible at [http://localhost:5050](http://localhost:5050).

---

## Feature Overview

Below is the overview of all 10 major features available in the system:

### 1. 📝 Posts
* **Main Function**: Article and long-form note publisher.
* **Short Description**: Allows creating and editing markdown posts. Supports tag organization, categorization, image uploads, and SQLite-backed FTS5 full-text search.

### 2. 📚 Series
* **Main Function**: Multi-part article binder.
* **Short Description**: Chains multiple standalone posts into structured series, creating next/previous page pagination and ordering for chapter-by-chapter reading.

### 3. 📖 Books & Reader
* **Main Function**: Digital library manager & immersive reader.
* **Short Description**: Organize book collections of chapters. Features an uploaded files section supporting **PDF, EPUB, MOBI, CBZ, FB2, XPS** formats. Offers a realistic **3D Page-Flip Reader** (spread-view for PDFs/Comics, responsive typography + TOC sidebar for EPUBs/MOBI), page jump, and resource deletion.

### 4. 🎧 TOEIC Test Preparation
* **Main Function**: Interactive practice sets for TOEIC training.
* **Short Description**: Features custom-formatted listening and reading tests. Users can select answers via radio inputs, play synced audio transcripts, submit answers for grade calculation, and view comprehensive explanation logs.

### 5. 🎵 Music Manager
* **Main Function**: Personal audio player and library organizer.
* **Short Description**: Supports importing audio files, editing track metadata, organizing songs into playlists, and playing them in a persistent audio drawer.

### 6. 🗒️ Notes
* **Main Function**: Quick-access, board-style sticky notes.
* **Short Description**: Simple grid layout for jotting down instant ideas. Notes can be tagged, pinned to the top of the feed, and rendered with custom background themes (plain, lines, dots, grid, sticky).

### 7. 📄 API Docs
* **Main Function**: REST API endpoint documentation.
* **Short Description**: Let developers document APIs. Groups API endpoints under projects, specifying request methods, URL paths, headers, query parameters, body schemas, and response formats in a beautiful schema view.

### 8. 🔖 Bookmarks
* **Main Function**: Link saver and cataloger.
* **Short Description**: Stores bookmarks and external links. Organize them with quick-filter tags and category folders.

### 9. ✅ Tasks
* **Main Function**: Task manager with version history.
* **Short Description**: Manage tasks with dynamic subtask checklists (status: to-do, in-progress, done) and notes. Updates are saved as individual historical files (`dd_mm_yyyy_user_name_updated_times.md`), letting users view previous versions or clear old histories.

### 10. ✉️ Email Composers
* **Main Function**: Template-based professional email compiler.
* **Short Description**: Drafting tool with 8 pre-seeded business templates (welcome emails, follow-ups, outreach). Custom variables (e.g. `{{name}}`) are extracted into interactive form inputs, rendering real-time draft previews with copy actions and direct `mailto` desktop client launch.
