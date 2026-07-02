# Report — TOEIC practice section (separate toeic/ folder)

- **Date:** 2026-06-28
- **Author:** Claude (AI agent)
- **Source:** User request — a TOEIC reading page; files stored in `toeic/` (not `posts/`); posts like Part 5/6/7; answers as radio buttons; correct answer + notes hidden behind a show/hide button.
- **Status:** ✅ Complete — 78/78 tests passing, verified live.

---

## 1. Objective

Add a self-contained **TOEIC practice** section that reads markdown files from a
**`toeic/`** folder (kept separate from `posts/`). Each file is a "set" tagged
with a part (5/6/7). Questions render with **radio-button** choices, and the
**correct answer + notes** stay hidden until the reader clicks **Show answer**.

## 2. What I did

| File | Change |
|------|--------|
| `app/config.py` | Added `toeic_dir` to `Settings` (default `toeic/`, configurable via `data.toeic_dir`). |
| `app/toeic.py` | **New.** Block-format parser (`::: passage … :::`, `::: question … :::`) → `ToeicSet`/`ToeicQuestion`; `ToeicManager.list()/read()` reading from `toeic/`. README and question-less files excluded from the index. |
| `app/main.py` | `ToeicManager` instance + routes `GET /toeic` (index, sorted by part) and `GET /toeic/{slug}` (detail). |
| `templates/toeic_list.html` | Set cards (part badge, question count, summary). |
| `templates/toeic_detail.html` | Optional passage, then each question: prompt + **radio choices** + **Show answer** toggle + hidden answer box (correct letter + note). "Show all answers" control. |
| `static/app.js` | `revealAnswer()` toggles the answer box, highlights the correct choice, and shows a ✓/✗ verdict vs. the selected radio; per-question + "show all" toggles. |
| `static/style.css` | TOEIC styles (question cards, choices, correct highlight, verdict, answer box). |
| `templates/base.html` | **🎧 TOEIC** button in the topbar (left of Series). |
| `config.yaml` | Documented `data.toeic_dir`. |
| `toeic/` | Seeded `part5-grammar-1.md`, `part7-reading-1.md`, and a `README.md` documenting the file format. |
| `tests/test_toeic.py` | 10 tests. `tests/test_phase5.py` updated for the new Settings field. |

### File format (authoring)
```markdown
---
title: "Part 5 — Grammar Set 1"
part: 5
---
::: passage
Optional markdown passage (Part 6/7).
:::
::: question
The board will _____ the budget.
- A. review
- B. reviews
answer: A
note: After **will**, use the base form.
:::
```
- Choices → radio buttons; `answer:` = correct letter; `note:` = markdown
  explanation (multi-line until the closing `:::`).
- Passage + note are rendered with mistune; prompt + choices are HTML-escaped.

### Design decisions
- **Separate folder + manager**, mirroring posts but with no FTS index — TOEIC
  sets are practice content, not searchable posts. Stored in `toeic/`, never
  `posts/`, exactly as requested.
- **Block fences (`:::`)** chosen over frontmatter-encoded questions: readable,
  supports markdown passages/notes, and parses unambiguously.
- **Radios are meaningful:** revealing the answer highlights the correct choice
  and grades the user's selection (✓ Correct / ✗ Incorrect) — beyond the minimum
  ask, but it's what makes the radios useful.
- **Per-question + "Show all"** toggles; everything works without JS for reading
  (answer box is just `hidden`, server-rendered).

## 3. Tests

`tests/test_toeic.py` (10) + prior suite (68) = **78 total**.

| Area | Tests |
|------|-------|
| Parser | structure, question fields, multi-line note, 2-choice question |
| Manager | list/read, README excluded, sort by part |
| Routes | topbar button, index lists sets, detail renders radios + hidden answer, 404, JS presence |

**Result:** `78 passed in 0.72s`.

**Live check** (uvicorn :5062): topbar TOEIC button present; index listed both
seeded sets (Part 5 & Part 7); detail rendered 12 radios (3×4), the answer in a
`hidden` box behind the toggle, "Correct answer: A" present, "Show all" control
present, README excluded. Seeded `toeic/` files kept (real content).

## 4. Environment notes

- No new dependencies (reuses mistune + python-frontmatter).
- `toeic/` is created on startup; needs a server **restart** (Python change).

## 5. How to verify (manual)

```bash
.venv/bin/python cli.py serve     # restart to pick up the new module/routes
# Click 🎧 TOEIC → open "Part 5 — Grammar Set 1" → pick a radio answer →
# click "Show answer": the correct choice highlights and a ✓/✗ verdict appears.
# Add your own sets by dropping .md files in toeic/ (see toeic/README.md).
```

## 6. Next steps / ideas

- A "Score" summary that grades all questions at once.
- Sort/filter the TOEIC index by part (like the Series page).
- An in-app editor for TOEIC sets (currently authored as files).
