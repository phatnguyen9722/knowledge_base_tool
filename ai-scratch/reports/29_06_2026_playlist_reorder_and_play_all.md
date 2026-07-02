# Report — Playlist reorder + "Play all" continuous mode

- **Date:** 2026-06-29
- **Author:** Claude (AI agent)
- **Source:** User request — reorder songs within a playlist and a "play all" continuous mode.
- **Status:** ✅ Complete — 170/170 tests passing, verified live.

---

## 1. Objective

1. **Reorder** songs within a playlist.
2. **Play all** — continuous playback that auto-advances through the playlist.

## 2. What I did

| File | Change |
|------|--------|
| `app/music.py` | `move_track(slug, track_slug, direction)` — swaps a track with its neighbor (`up`/`down`); edge moves are a safe no-op. |
| `app/main.py` | `POST /music/playlists/{slug}/move` (track + direction; rejects bad direction). |
| `templates/playlist_detail.html` | Per-track **▲/▼ reorder** buttons (disabled at the ends); a **Play-all bar** (▶ Play all button, "Now playing" label, one `<audio>`); track URLs emitted as JSON for the player. |
| `static/app.js` | `initPlaylistPlayer()` — reads the JSON track list, plays in order, **auto-advances on `ended`**, updates "Now playing", and highlights the current row. |
| `static/style.css` | Play-all bar, reorder buttons, and `.playing` highlight. |

## 3. Design decisions

- **Up/down reorder (not drag):** simple, accessible, and works without JS — each
  arrow is a tiny POST form; the server swaps and redirects. Arrows are disabled
  at the first/last position.
- **Play-all is progressive-enhancement JS:** a single `<audio>` element whose
  `src` is swapped to the next track on the `ended` event. The track list is
  passed as a `<script type="application/json">` blob (built with Jinja `tojson`,
  so titles/URLs are safely escaped) — no extra endpoint needed.
- **Only playable tracks** (those with an audio file) are included in the
  play-all sequence (`selectattr('audio_url')`).
- **Current track highlight** via a `.playing` class toggled by slug, reusing the
  pinned-style accent border.

## 4. Tests

`tests/test_playlist_reorder.py` (8) + prior suite (162) = **170 total**.

| Area | Tests |
|------|-------|
| `move_track` | down/up swap, edge no-op, unknown track/playlist |
| Routes | move reorders + 303, bad direction → 404 |
| Template/JS | play-all bar + `pa-data` + reorder buttons + `initPlaylistPlayer()`; app.js has the player + `ended` auto-advance |

**Result:** `170 passed in 1.12s`. `node --check static/app.js` → OK.

> The actual audio playback/auto-advance is browser-only; verified via the
> rendered player markup, the JSON track data, and the JS presence + syntax.

**Live check** (uvicorn :5074): a 3-track "Mix" → play-all bar with all 3 audio
URLs present; moving "First" down reordered `[first, second, third]` →
`[second, first, third]`. Test files cleaned up.

## 5. How to verify (manual)

```bash
.venv/bin/python cli.py serve     # restart for the move route
# 🎵 Music → ▶ Playlists → open a playlist with 2+ songs:
#   • use ▲/▼ to reorder songs
#   • click "▶ Play all" — it plays through, auto-advancing, highlighting the
#     current track, and shows "Now playing: …".
```

## 6. Next steps / ideas

- Drag-and-drop reordering (HTML5 DnD) as an upgrade over arrows.
- Prev/next buttons + shuffle/repeat on the play-all bar.
- Persist playback position across pages (mini-player).
