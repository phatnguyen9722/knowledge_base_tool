# Report — Song lyrics with show/hide

- **Date:** 2026-06-28
- **Author:** Claude (AI agent)
- **Source:** User request — add lyric content for each song, with show/hide.
- **Status:** ✅ Complete — 121/121 tests passing, verified live.

---

## 1. Objective

Let each song carry **lyrics**, editable per track, and shown behind a
**show/hide** toggle on the Music page.

## 2. What I did

| File | Change |
|------|--------|
| `app/music.py` | `Track` gained `lyrics` (stored as the markdown **body**, line breaks preserved). `notes` moved to a frontmatter field (short note). `update()` writes notes→frontmatter + lyrics→body; `read()` reads them back accordingly. |
| `app/main.py` | `/music/{slug}/edit` POST accepts a `lyrics` field. |
| `templates/music_edit.html` | A **Lyrics** textarea (+ notes as a short input). |
| `templates/music_list.html` | Lyrics shown via a native `<details><summary>Lyrics</summary><pre>…</pre></details>` show/hide. |
| `static/style.css` | `.lyrics-details` / `.lyrics` styling (pre-wrap so line breaks render). |
| `tests/test_music_lyrics.py` | 4 tests. |

### Design decisions
- **Lyrics stored as the markdown body**, not frontmatter — multi-line lyrics
  belong in the body (YAML multiline is ugly), and the body preserves line
  breaks verbatim. `notes` became a separate short frontmatter field.
- **Native `<details>` for show/hide** — no JS needed, accessible, and keyboard-
  operable; collapsed by default.
- **`<pre class="lyrics">` with `white-space: pre-wrap`** so each lyric line
  shows on its own line (rendering as markdown would collapse single newlines).

## 3. Tests

`tests/test_music_lyrics.py` (4) + prior suite (117) = **121 total**.

| Test | Covers |
|------|--------|
| `test_lyrics_persist_with_line_breaks` | lyrics saved to body w/ newlines; notes separate |
| `test_edit_form_has_lyrics_field` | edit form exposes the lyrics field |
| `test_lyrics_show_hide_on_index` | `<details>/<summary>` + lyrics text on the index |
| `test_no_lyrics_block_when_empty` | no toggle when a track has no lyrics |

**Result:** `121 passed in 0.83s`.

**Live check** (uvicorn :5067): imported a track, added lyrics via the edit form,
and the index showed the collapsible "Lyrics" toggle with the multi-line text
preserved. Test files cleaned up.

## 4. How to verify (manual)

```bash
.venv/bin/python cli.py serve     # restart for the route change
# 🎵 Music → Edit a track → paste lyrics → Save → on /music click "Lyrics"
# to expand/collapse the lyric text.
```

## 5. Next steps / ideas

- Synced/timed lyrics (LRC) that highlight with playback.
- Search across lyrics.
