# Report — TOEIC Listening Parts 1-4 (old & new format)

- **Date:** 2026-06-29
- **Author:** Claude (AI agent)
- **Source:** User request — implement TOEIC Parts 1-4 Listening (old format and new format).
- **Status:** ✅ Complete — 185/185 tests passing, verified live.

---

## 1. Objective

Add a dedicated TOEIC Listening section covering all four listening parts of
the TOEIC exam, supporting both the **old format** (pre-2016) and **new format**
(post-2016), with audio players, photo/graphic display, radio-button choices,
and show/hide answers.

---

## 2. TOEIC Listening formats

| Part | Old Format | New Format |
|------|-----------|------------|
| **1 — Photographs** | 20 photos, 4 choices | 6 photos, 4 choices |
| **2 — Question-Response** | 30 items, 3 choices | 25 items, 3 choices |
| **3 — Conversations** | 10 conversations × 3 Qs = 30 | 13 × 3 = 39 (may include 3-speaker, graphics) |
| **4 — Short Talks** | 10 talks × 3 Qs = 30 | 10 × 3 = 30 (may include reference graphics) |

---

## 3. What I did

| File | Change |
|------|--------|
| `app/toeic.py` | New dataclasses: `Photograph`, `QRPair`, `ListeningQuestion`, `ListeningGroup`, `ListeningSet`. A nested-block parser (`parse_listening`) handles `::: photo`, `::: qr`, `::: group` (with nested `::: cq`). `ToeicManager` extended with `create_listening`, `read_listening`, `raw_listening`, `list_listening` — listening files are stored as `l-<slug>.md`, detected by `type: listening` frontmatter. |
| `app/main.py` | `/toeic-audio` static mount (→ `toeic/audio/`); `POST /api/upload-audio` endpoint (accepts mp3/ogg/wav/aac/m4a, SHA-256-named, returns `/toeic-audio/...`); routes for `/toeic/listening`, `/new`, `/{slug}`, `/{slug}/edit`. |
| `templates/listening_list.html` | Index grouped by part (1→2→3→4) with NEW/OLD badges, item/group counts. |
| `templates/listening_detail.html` | Per-part layout: **Part 1** — photo grid + audio player + A–D choices; **Part 2** — QR list + audio + transcript + A–C choices; **Parts 3 & 4** — group list each with audio, collapsible transcript, and numbered sub-questions with choices. All items use the existing `data-answer-toggle` + `toeic-toggle-all` reveal/hide + verdict highlighting. |
| `templates/listening_editor.html` | Editor with part/format selects, audio upload widget (upload → URL), and a collapsible format guide showing all block types. |
| `toeic/l-*.md` | Seeded 5 example files: Part 1 (new + old), Part 2 (new), Part 3 (new, 3 conversations), Part 4 (new, 3 talks). |
| `static/style.css` | Listening-specific CSS: photo grid, QR heads, group cards, transcript details, graphic support, listening info bar, upload bar, format guide. |

### File format (in `toeic/`)
Listening files are named `l-<slug>.md` and carry `type: listening` frontmatter.

**Part 1:**
```
::: photo
image: /img/office.jpg
audio: /toeic-audio/p1-q1.mp3
- A. A woman is typing on a laptop.
- B. A man is reading a book.
answer: A
note: The woman is clearly working on her laptop.
:::
```

**Part 2:**
```
::: qr
audio: /toeic-audio/p2-q1.mp3
transcript: "Where did you put the report?"
- A. I left it on your desk.
- B. Yes, it was impressive.
- C. It takes about an hour.
answer: A
:::
```

**Parts 3 & 4 (with nested questions):**
```
::: group
audio: /toeic-audio/p3-c1.mp3

Man: I'd like to return this jacket.
Woman: Do you have a receipt?

::: cq
Why is the man at the store?
- A. To buy a jacket
- B. To return a purchase
answer: B
graphic: /img/optional-reference.png
note: "I'd like to return this jacket."
:::
:::
```

### Design decisions
- **`l-` file prefix** prevents slug collision with reading sets; `type: listening` frontmatter keeps them separated in `list()` vs `list_listening()`.
- **Audio is optional in every block** — sets work as written-practice even without audio files. When audio is present, the browser's native `<audio>` player renders inline.
- **Nested-block parser** uses a depth counter to correctly handle `::: group` containing `::: cq` blocks (the closing `:::` of a `cq` is depth-1, while the closing `:::` of a `group` is depth-0).
- **Audio upload at `/api/upload-audio`** stores files in `toeic/audio/` (separate from music), serves at `/toeic-audio/`, uses SHA-256 content addressing (same dedup design as image uploads).
- **New-format features** (graphics in Part 3/4, 3-speaker conversations): the `graphic:` field on `cq` blocks displays a reference image above the question; multi-speaker transcripts are plain text (the format already supports any number of speakers naturally).

---

## 4. Tests

`tests/test_toeic_listening.py` (15) + prior suite (170) = **185 total**.

| Area | Tests |
|------|-------|
| Parser | Part 1 photographs (image/audio/choices/answer/note), Part 2 QR pairs (transcript/choices), Part 3 nested groups+cq, Part 4 old format, invalid format defaults to new |
| Manager | create+read, listening separate from reading in `list()`, sorted by part |
| Routes | index, new form per-part, create+detail (radios/show-all), Part 3 transcript, 404, audio upload endpoint |
| Seeded files | every `l-*.md` parses without error |

**Result:** `185 passed in 1.37s`.

**Live check** (uvicorn :5075):
- Index grouped Part 1→4, NEW/OLD badges.
- Part 3 detail: 3 groups, Transcript toggles, radios, show-all button.
- Part 4 detail: Short Talks label, radios.
- Editor: Part 2 skeleton + audio upload widget.

---

## 5. How to use

```bash
.venv/bin/python cli.py serve     # restart for new routes/mount
# 🎧 TOEIC → 🎵 Listening (Parts 1-4) → open a seeded set
# or + New Set → pick Part + Format → write blocks → Save
# Upload audio via the "Upload audio" bar → paste the returned URL
#   into audio: / graphic: fields in the markdown
```

---

## 6. Next steps

- Drag-and-drop audio upload directly into the editor textarea.
- Import/link audio from the Music library.
- A timer mode for realistic test simulation.
- Statistics: score tracking across listening sets.
