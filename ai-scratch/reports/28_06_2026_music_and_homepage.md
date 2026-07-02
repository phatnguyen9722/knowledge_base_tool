# Report — Music section + Homepage

- **Date:** 2026-06-28
- **Author:** Claude (AI agent)
- **Source:** User request — (1) a Music page: import .mp3 → store in `music/` + a generated markdown file the user can edit (author, year, type, …); (2) a Homepage showing all features as item boxes.
- **Status:** ✅ Complete — 117/117 tests passing, verified live end-to-end.

---

## 1. Objective

1. **Music**: import `.mp3` files (stored in `music/`), auto-generate an editable
   markdown sidecar per track (title, author, year, type, album, notes), play
   tracks in-browser.
2. **Homepage** at `/` presenting every section as a clickable box. (This moves
   the posts feed from `/` to `/posts`.)

## 2. What I did

### Music
| File | Change |
|------|--------|
| `app/config.py` | `music_dir` setting (default `music/`). |
| `app/music.py` | **New.** `Track` dataclass + `MusicManager`: `import_track` (saves `<slug>.mp3` + generates `<slug>.md`), `read`, `list`, `update`, `delete`. |
| `app/main.py` | `MusicManager` instance; `/audio` static mount for the mp3s; routes: `GET /music`, `POST /music/import`, `GET/POST /music/{slug}/edit`, `POST /music/{slug}/delete`. |
| `templates/music_list.html` | Import button (file picker auto-submits), track cards with **`<audio>` players** + metadata + Edit. |
| `templates/music_edit.html` | Player + metadata fields (author/year/type/album) + notes + Delete. |
| `templates/base.html` | **🎵 Music** topbar button. |
| `static/style.css` | Music cards / audio styling. |

### Homepage
| File | Change |
|------|--------|
| `app/main.py` | `GET /` now renders `home.html` with a feature list (icon, title, desc, live count). Posts feed moved to `GET /posts`; `_build_url` now targets `/posts`. |
| `templates/home.html` | **New** feature-box grid (Posts, Series, Books, TOEIC, Music). |
| `templates/base.html` | Search form posts to `/posts`; brand still links to `/` (homepage). |
| `templates/list.html`, `templates/detail.html` | Post tag links + Back link updated to `/posts`. |
| `static/style.css` | `.home-grid` / `.home-card` styling. |

## 3. Design decisions

- **Audio served at `/audio`, not `/music`.** A `StaticFiles` mount at `/music`
  would shadow the `/music/*` app routes (POST → 405). The mp3s live in
  `music/` on disk but are served via a separate `/audio/<slug>.mp3` mount.
- **Import → edit flow:** importing redirects straight to the edit form so the
  user can fill in metadata immediately (title defaults to the filename).
- **mp3 + markdown sidecar** (`<slug>.mp3` + `<slug>.md`) keeps audio and
  editable metadata together, mirroring the posts/books pattern.
- **Validation:** `.mp3`/`audio/mpeg` only, non-empty, ≤30 MB.
- **`/` becomes the homepage**, posts move to `/posts`. The brand links home;
  the search bar and post tag/back links were repointed to `/posts`. Counts on
  the homepage are computed live from each manager.

## 4. Tests

`tests/test_music.py` (15: manager + routes + homepage) + prior suite — **117 total**.
Updated posts-feed tests (`test_api`, `test_phase4`, `test_toeic_create`) to use
`/posts` now that `/` is the homepage; `test_phase5` got the new `music_dir`.

| Area | Tests |
|------|-------|
| Manager | import creates mp3+md, update metadata, unique slug, delete both files |
| Routes | topbar button, empty index, import→edit redirect, reject non-mp3, edit+list, delete |
| Homepage | feature boxes render all section links; posts feed lives at `/posts` |

**Result:** `117 passed in 0.80s`.

**Live check** (uvicorn :5066): homepage rendered all five boxes; imported
`Imagine.mp3` → redirected to its edit form → set author/year/type → index
showed the metadata + `<audio>` player; `/audio/imagine.mp3` served the exact
bytes. Test files cleaned up.

## 5. Environment notes

- No new dependencies (reuses frontmatter + slugify; HTML5 `<audio>` for playback).
- New Python routes/mount need a server **restart**.

## 6. How to verify (manual)

```bash
.venv/bin/python cli.py serve     # restart for the new routes/mount
# Home (/) shows the feature boxes. 🎵 Music → + Import .mp3 → pick a file →
# you land on its edit form → fill author/year/type → Save → play it on /music.
```

## 7. Next steps / ideas

- Tag/genre filtering on the Music index; album grouping.
- Extract duration/ID3 tags on import (needs a library like mutagen).
- A "currently playing" persistent mini-player across pages.
