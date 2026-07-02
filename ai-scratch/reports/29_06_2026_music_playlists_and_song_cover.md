# Report — Music: playlists + per-song cover

- **Date:** 2026-06-29
- **Author:** Claude (AI agent)
- **Source:** User request — add a playlist feature for Music, and a cover image for each song.
- **Status:** ✅ Complete — 163/163 tests passing, verified live.

---

## 1. Objective

1. **Per-song cover** image (like book collections).
2. **Playlists** — create a playlist, then add/remove songs.

## 2. What I did

### Per-song cover
| File | Change |
|------|--------|
| `app/music.py` | `Track.cover`; written on import (`""`), editable via `update`, read back. |
| `app/main.py` | `/music/{slug}/edit` accepts a `cover` field. |
| `templates/music_edit.html` | Cover file-picker + URL field + preview (reuses `initCoverUpload` → `/api/upload`). |
| `templates/music_list.html` | Track cards show a cover thumbnail (or 🎵 placeholder), in a flex layout. |

### Playlists
| File | Change |
|------|--------|
| `app/music.py` | `Playlist` dataclass + manager methods: `create_playlist`, `read_playlist` (resolves track slugs → `Track`s in order, dropping deleted ones), `list_playlists`, `add_to_playlist`, `remove_from_playlist`, `delete_playlist`. Stored as `music/playlists/<slug>.md` (frontmatter: title, description, `tracks: [slug…]`). |
| `app/main.py` | Routes `GET /music/playlists`, `GET/POST /music/playlists/new`, `GET /music/playlists/{slug}`, `POST …/add`, `POST …/remove`, `POST …/delete`. |
| `templates/` | `playlists_list.html` (index + New), `playlist_edit.html` (create), `playlist_detail.html` (numbered track list w/ players, add-song `<select>`, remove, delete). |
| `templates/music_list.html` | "▶ Playlists" link in the header. |
| `static/style.css` | Track cover + flex card; playlist add-form + numbered track list. |

## 3. Design decisions

- **Playlists store track *references*** (`tracks: [slug…]`), not copies — the
  mp3/metadata stay single-source in `music/`. `read_playlist` resolves them in
  saved order and **silently drops tracks that were deleted** (slug stays in the
  file but isn't shown), so a deleted song never breaks a playlist.
- **Stored under `music/playlists/`** — keeps playlists with the music data;
  `list()` only globs top-level `*.md`, so playlists aren't mistaken for tracks.
- **Route ordering:** the `/music/playlists*` routes are registered **before**
  `/music/{slug}/*`, so "playlists" isn't captured as a track slug (covered by a
  test).
- **Cover reuses the shared upload pipeline** (`/api/upload` → `/img/`), exactly
  like book covers; the field also accepts a pasted URL.
- **Add-song UX:** the playlist page offers a `<select>` of tracks **not already
  in** the playlist; each track row has a Remove button. Adding is idempotent.

## 4. Tests

`tests/test_music_playlists.py` (13) + prior suite (152) = **163 total**.

| Area | Tests |
|------|-------|
| Cover | defaults empty → set; edit form has field; shows on index |
| Playlist manager | create/add/remove (ordered, idempotent), missing track/playlist, files under `music/playlists/`, deleted track drops from view |
| Routes | Playlists link, routes not shadowed, create→add→remove flow, delete |

**Result:** `163 passed in 1.09s`.

**Live check** (uvicorn :5073): imported two tracks, set a cover on one (shows on
the index), created the "Classics" playlist, added both songs (page showed "2
tracks", the cover, and the add-song form), and it appeared on the playlists
index. Test files cleaned up.

## 5. How to verify (manual)

```bash
.venv/bin/python cli.py serve     # restart for the new routes
# 🎵 Music → Edit a track → set a Cover image (upload/preview) → Save.
# 🎵 Music → ▶ Playlists → + New Playlist → open it → "Add a song…" select → + Add.
```

## 6. Next steps / ideas

- Reorder songs within a playlist (drag, or up/down).
- "Play all" / continuous playback across a playlist.
- Rename/edit a playlist's title & description.
