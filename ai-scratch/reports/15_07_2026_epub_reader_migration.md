# EPUB Reader Migration Report

## The Problem
In the initial version, the app attempted to parse EPUB files natively on the backend using Python (`ebooklib` / `PyMuPDF`). The server extracted the HTML `<body>` tags of each chapter, cleaned the HTML via Regex, and injected it into an `<iframe>` in the browser. 

This approach suffered from several major issues:
1. **CSS Collisions (Collapsing Text)**: Every publisher encodes EPUB styles differently. Inline attributes like `position: absolute` or custom `line-heights` bypassed our regex cleaners, causing text to severely overlap and break the layout.
2. **Artificial Pagination**: Breaking an EPUB into accurate "pages" is impossible on the backend without knowing the user's screen size, zoom level, and font settings.
3. **Complex Backend Logic**: The Python codebase was burdened with messy, regex-heavy HTML sanitization routines that were slow and fragile.

## The New Approach
To resolve these issues, we completely shifted the architecture from **Server-Side Rendering** to **Client-Side Rendering** using **`epub.js`**.

### Architecture Changes
1. **Backend Simplicity (Zero Parsing)**
   - **Removed**: The complex `resource_text_chapters()` Python parsing method is no longer used for EPUBs.
   - **Added**: A simple streaming endpoint (`/books/{coll}/resources/download/{fname}`) was created. This endpoint serves the raw, unmodified `.epub` archive directly to the frontend.

2. **Frontend Engine (`epub.js`)**
   - The frontend now loads `epub.min.js` and `jszip.min.js` via jsDelivr CDN.
   - When the user opens a text book, the browser fetches the raw `.epub` file, unzips it in memory, and mounts it into the `#epub-viewer` container.

### Key Benefits Achieved
1. **Flawless 2-Page Spreads**: `epub.js` precisely calculates the exact dimensions of the browser window and natively splits the content into perfect two-page spreads (just like the PDF reader).
2. **CSS Isolation**: The engine mounts the book inside secure Shadow DOMs/iframes, totally neutralizing publisher CSS and preventing text overlapping. We inject our custom theme (`Georgia`, `1.05rem`, `#f5f0e8` parchment background) seamlessly over it.
3. **True Pagination**: Because it measures the text on the client-side, the text naturally reflows and never breaks out of the container. If the user zooms in, `epub.js` simply recalculates the pages.
4. **CFI Progress Tracking**: Progress tracking is now highly accurate. Instead of dividing chapters, it uses CFI (Canonical Fragment Identifier) metrics to pinpoint exactly what percentage of the book the user has read (e.g., `45% Read`). 

## Summary
By removing EPUB parsing from Python and trusting the browser's rendering engine via `epub.js`, the app is now dramatically faster, entirely resilient to bad publisher CSS, and provides a premium, true-to-life reading experience.
