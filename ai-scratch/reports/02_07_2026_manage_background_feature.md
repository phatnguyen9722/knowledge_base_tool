# Manage Background Feature

**Date:** 02/07/2026  
**Tasks:**
1. Add "Background" panel to Settings modal
2. Serve built-in default background from `static/`
3. Support uploading custom backgrounds (stored in `img/background/`)
4. Apply background via CSS custom properties with no-flash on load
5. Opacity and size controls for active background
6. Docker compatibility — default available without volume seeding

---

## 1. Settings Panel: Background

### Feature
A new **🌄 Background** nav item and panel was added to the existing two-panel Settings modal. It gives users three choices:

- Click a **Built-in** thumbnail (shipped with the app) to apply it immediately.
- **Upload** a custom image (PNG / JPG / WEBP / GIF, max 10 MB) via drag-and-drop or file picker.
- Click **✕ Remove Background** to revert to the default app colour.

### Implementation

**`templates/base.html`**
- Added `<button class="settings-nav-item" data-panel="background">🌄 Background</button>` to the settings sidebar.
- Added `#panel-background` with two sub-sections:
  - **Built-in** — `#bg-defaults-gallery` renders static thumbnails from `BG_DEFAULTS`.
  - **Uploaded** — `#bg-gallery` renders user-uploaded images fetched from `/api/backgrounds`.
- Dropzone placed under the "Uploaded" heading; it accepts both click-to-browse and drag-and-drop.
- Size selector (`cover` / `contain` / `auto tile`) and opacity slider (10–100%) appear in `#bg-controls` only when a background is active.
- **No-flash inline `<script>` in `<head>`** — reads `kb-background` from `localStorage` and immediately sets `--kb-bg-url`, `--kb-bg-size`, and `--kb-bg-opacity` CSS custom properties before first paint, preventing a blank flash on hard refresh.

```html
<!-- No-flash restore (inside <head>) -->
var kbBg = JSON.parse(localStorage.getItem("kb-background") || "null");
if (kbBg && kbBg.url) {
  document.documentElement.style.setProperty("--kb-bg-url", "url('" + kbBg.url + "')");
  document.documentElement.style.setProperty("--kb-bg-size", kbBg.size || "cover");
  document.documentElement.style.setProperty("--kb-bg-opacity", kbBg.opacity / 100);
}
```

---

## 2. Built-in Default Background

### Feature
`background_1.svg` is stored in `static/` — the same directory as `app.js` and `style.css` — so it is:
- Served at `/static/background_1.svg` with zero configuration.
- Automatically included in every Docker image build (`COPY static/ /app/static/`).
- Available immediately in both local dev and Docker without any volume setup.

### Implementation

**`static/app.js`**
- `BG_DEFAULTS` array declares all built-in backgrounds:

```js
var BG_DEFAULTS = [
  { url: "/static/background_1.svg", label: "Background 1" },
];
```

- Adding more built-in backgrounds is one line: drop a file in `static/` and append an entry to `BG_DEFAULTS`.
- Built-in items render with an **Active** badge on selection but have **no delete button**.

---

## 3. Custom Background Upload API

### Feature
Three new API endpoints mirror the existing icon upload pattern:

| Method | Route | Description |
|--------|-------|-------------|
| `POST` | `/api/upload-background` | Upload image; de-duped by SHA-256 hash |
| `GET` | `/api/backgrounds` | List all uploaded backgrounds (newest first) |
| `DELETE` | `/api/backgrounds/{filename}` | Delete a specific background |

Files are stored in `img/background/` (auto-created on startup).

**`app/main.py`**
- `BG_DIR = IMG_DIR / "background"` — declared alongside existing `IMG_DIR`.
- `BG_DIR.mkdir(parents=True, exist_ok=True)` — created on app startup.
- Same 10 MB size limit and image type validation as the icon upload endpoint.
- Path-traversal protection on the delete endpoint (`/`, `\`, `..` rejected).

```python
@app.post("/api/upload-background")
async def upload_background(file: UploadFile = File(...)):
    ...
    return {"url": f"/img/background/{filename}", "filename": filename}

@app.get("/api/backgrounds")
async def list_backgrounds():
    ...

@app.delete("/api/backgrounds/{filename}")
async def delete_background(filename: str):
    ...
```

---

## 4. Background Applied via CSS Custom Properties

### Feature
The background is rendered by a `body::before` pseudo-element driven by three CSS variables. This keeps the background visually behind all app content without any layout side-effects.

**`static/style.css`**

```css
:root {
  --kb-bg-url: none;
  --kb-bg-size: cover;
  --kb-bg-opacity: 1;
}
body::before {
  content: "";
  position: fixed;
  inset: 0;
  z-index: -1;
  background-image: var(--kb-bg-url);
  background-size: var(--kb-bg-size);
  background-position: center center;
  background-repeat: no-repeat;
  opacity: var(--kb-bg-opacity);
  pointer-events: none;
}
```

**`static/app.js`** — `_applyBg(pref)` sets/removes the variables at runtime:

```js
function _applyBg(pref) {
  var root = document.documentElement;
  if (pref && pref.url) {
    root.style.setProperty("--kb-bg-url", "url('" + pref.url + "')");
    root.style.setProperty("--kb-bg-size", pref.size || "cover");
    root.style.setProperty("--kb-bg-opacity", pref.opacity / 100);
  } else {
    root.style.removeProperty("--kb-bg-url");
    // ...
  }
}
```

User preference (`url`, `size`, `opacity`) is persisted to `localStorage` under the key `kb-background`.

---

## 5. Opacity and Size Controls

### Feature
When any background is active, a control bar appears above the gallery:

- **Size** — dropdown: `Cover (fill)` / `Contain (fit)` / `Auto (tile)`
- **Opacity** — range slider 10–100%, live preview as the slider moves

Changes are applied immediately to the page and saved to `localStorage`.

---

## 6. Docker Compatibility

### Problem
Previous attempt used an `entrypoint.sh` script to seed `img/background/` from a bundled copy inside the image on first boot. This was complex and fragile (volume timing, cache invalidation, 304 Not Modified on static assets after rebuild).

### Final Solution
Moving the default to `static/background_1.svg` eliminates all seeding complexity:

- `static/` is always `COPY`-ed into the image at build time.
- No entrypoint script needed.
- The `RUN touch /app/static/style.css /app/static/app.js` line in the Dockerfile resets file mtimes to the **build timestamp**, ensuring the `?v=` cache buster always changes after `--build`, preventing browsers from serving stale JS/CSS.

```dockerfile
COPY static/ /app/static/
# Bust browser cache on every rebuild
RUN touch /app/static/style.css /app/static/app.js
```

---

## Files Changed

| File | Change |
|------|--------|
| `templates/base.html` | Added Background nav item, panel HTML (Built-in + Uploaded sections), no-flash `<head>` script |
| `static/app.js` | Added `BG_DEFAULTS`, `_applyBg`, `_uploadBgFile`, `_renderBgDefaultsGallery`, `_renderBgUploadsGallery`, `loadBgPanel`, wired into `showSettingsPanel` |
| `static/style.css` | Added `body::before` background overlay, dropzone, gallery grid, controls, `.bg-gallery-title` styles |
| `app/main.py` | Added `BG_DIR`, `POST /api/upload-background`, `GET /api/backgrounds`, `DELETE /api/backgrounds/{filename}` |
| `static/background_1.svg` | Default background image (moved here from `img/background/`) |
| `dockerise/Dockerfile` | Added `RUN touch` to bust static asset browser cache on rebuild |
