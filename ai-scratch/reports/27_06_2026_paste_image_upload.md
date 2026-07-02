# Report — Paste image into editor → stored in img/

- **Date:** 2026-06-27
- **Author:** Claude (AI agent)
- **Source:** User request — paste an image in the markdown editor; store it in an `img/` folder alongside `posts/`.
- **Status:** ✅ Complete — 62/62 tests passing, verified live end-to-end.

---

## 1. Objective

Let a user **paste an image** in the editor; the app uploads it, stores it in an
`img/` directory (sibling of `posts/`), and inserts a markdown image link at the
cursor.

## 2. What I did

| File | Change |
|------|--------|
| `app/config.py` | Added `img_dir` to `Settings`; defaults to `posts/`'s sibling `img/` (overridable via `data.img_dir`). |
| `app/main.py` | Mounts `/img` (static); `POST /api/upload` validates type/size, writes the file, returns `{url, markdown, filename}`. `IMG_DIR` is created at startup. |
| `static/app.js` | Editor `paste` listener detects image clipboard items → `uploadImage()` inserts an `![uploading…]()` placeholder, POSTs to `/api/upload`, then swaps in the returned markdown (or removes the placeholder on failure). |
| `templates/editor.html` | Placeholder hint: "paste an image to upload it". |
| `config.yaml` | Documented `data.img_dir: img`. |
| `tests/test_upload.py` | 5 tests. `tests/test_phase5.py` updated for the new `Settings` field. |

### Storage / naming
- Files go to `img/` next to `posts/` — e.g. `img/ebf4f635a17d10d6.png`.
- **Content-addressed names:** filename = first 16 hex of the SHA-256 of the
  bytes + the type's extension. So pasting the same image twice **dedupes**
  (one file), and names never collide.
- Served at `/img/<filename>`; the inserted markdown is `![](/img/<filename>)`.

### Validation
- Allowed types: png, jpeg, gif, webp, svg, bmp (by `Content-Type`).
- Rejects non-images (400), empty files (400), and >10 MB (413).

### Design decisions
- **Content-addressed over timestamped names:** deterministic, dedupes, and
  avoids needing a clock (the workflow scripts ban `Date.now()`, but more
  importantly it keeps the img/ folder clean across re-pastes).
- **Optimistic placeholder** (`![uploading…]()`) so the editor feels responsive;
  it's replaced on success or cleaned up on error.
- **Paste, not drag-drop** for now (the request was paste); drag-drop could reuse
  `uploadImage()` later.
- `img_dir` resolves relative to `posts_dir.parent`, so it stays a sibling of
  `posts/` even if the posts dir is relocated via config.

## 3. Tests

`tests/test_upload.py` (5) + prior suite (57) = **62 total**.

| Test | Covers |
|------|--------|
| `test_upload_png_saves_and_returns_markdown` | saves to img/, returns correct url + markdown |
| `test_upload_is_content_addressed_and_dedupes` | identical bytes → one file |
| `test_upload_rejects_non_image` | 400 on text/plain |
| `test_upload_rejects_empty` | 400 on empty |
| `test_app_js_has_paste_upload_logic` | JS has paste → /api/upload |

**Result:** `62 passed in 0.65s`.

**Live check** (uvicorn :5060): posted a 1×1 PNG → response
`{"url": "/img/ebf4f635a17d10d6.png", "markdown": "![](/img/ebf4f635a17d10d6.png)"}`;
fetching that URL returned the identical bytes. Verified `img/` contained the
file; cleaned up afterward.

## 4. Environment notes

- Uses `python-multipart` (already required by FastAPI form/upload routes).
- `IMG_DIR` is created on startup; needs a server **restart** (Python change).
  The JS/template/CSS parts auto-cache-bust via `?v=`.

## 5. How to verify (manual)

```bash
.venv/bin/python cli.py serve     # restart to pick up app changes
# New/Edit a post → copy an image (screenshot) → paste into the editor:
# an ![](/img/<hash>.png) link is inserted and the image renders in the preview.
# The file is on disk under img/ next to posts/.
```

## 6. Next steps / ideas

- Drag-and-drop upload (reuse `uploadImage()`).
- Optional image cleanup tool: find img/ files no post references.
- Configurable max size / allowed types.
