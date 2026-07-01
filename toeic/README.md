# TOEIC practice files

Drop markdown files here (one per practice set). They appear under **🎧 TOEIC**
in the app and are kept **separate from `posts/`**.

## File format

```markdown
---
title: "Part 5 — Grammar Set 1"   # required
part: 5                            # 5 | 6 | 7  (shown as a badge, used to sort)
created: 2026-06-28
updated: 2026-06-28
summary: "Optional one-line blurb"
tags: [grammar, part5]
---

::: passage
Optional reading passage in **markdown** (used for Part 6 / 7).
:::

::: question
The prompt / sentence, with a _____ blank if needed.
- A. choice one
- B. choice two
- C. choice three
- D. choice four
answer: B
note: Explanation in **markdown** — shown only when the reader clicks "Show answer".
:::
```

## Rules

- Wrap each question in `::: question` … `:::`, and each passage in
  `::: passage` … `:::`.
- Choices are lines like `- A. text` (the letter may use `.` or `)`).
- `answer:` is the correct letter; `note:` is the explanation (can span multiple
  lines until the closing `:::`).
- In the app, choices render as **radio buttons**; the correct answer and note
  stay hidden behind a **Show answer** toggle (per question, or "Show all").
