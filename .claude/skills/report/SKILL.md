---
name: report
description: >-
  Write a standardized work report after completing any task or set of actions
  in this project. Use whenever work is finished (a phase, a feature, a fix, a
  refactor) and the user wants it documented — or proactively after any
  substantive action. Reports go to ./ai-scratch/reports/dd_mm_yyyy_short_description.md
---

# Report

Document what was done in a consistent, reviewable format. Write one report per
task/work-session into `./ai-scratch/reports/`.

## When to use

- After completing a phase, feature, bugfix, or refactor.
- Whenever the user asks for a report, summary, or write-up of work done.
- Proactively at the end of any substantive set of actions in this project.

## Filename convention

```
./ai-scratch/reports/dd_mm_yyyy_short_description.md
```

- `dd_mm_yyyy` — the current date. Get it from the `currentDate` in project
  context (CLAUDE.md) or `date +%d_%m_%Y`. Example: `26_06_2026`.
- `short_description` — lower_snake_case, a few words. Example:
  `phase1_scaffold_data_model`.
- Create `./ai-scratch/reports/` if it does not exist.

## Required template

Fill every section. Omit a section only if it is genuinely not applicable, and
say so explicitly rather than leaving it blank.

```markdown
# Report — <Title>

- **Date:** YYYY-MM-DD
- **Author:** Claude (AI agent)
- **Source spec:** <file / ticket / request this work came from>
- **Status:** <✅ Complete | 🚧 In progress | ⛔ Blocked> — <one-line summary>

---

## 1. Objective
What was asked for and why.

## 2. What I did
Concrete actions taken. Use a file table for created/changed files:

| File | Purpose |
|------|---------|
| ...  | ...     |

### Design decisions / deviations
Anything done differently from the spec, and why. Be explicit about deviations.

## 3. Tests
What was tested and the actual result (paste the pass/fail summary line).
If nothing was tested, say so and why.

## 4. Environment notes
Versions, pins, gotchas, anything that affects reproducibility.

## 5. Checklist status
Mirror the source spec's checklist with [x]/[ ] so progress is auditable.

## 6. How to verify
Exact commands the reader can run to reproduce the result.

## 7. Next steps
What comes next (e.g. the next phase), as a short actionable list.
```

## Rules

- **Be truthful.** Report failures, skipped steps, and blockers plainly. If
  tests failed, paste the failure. Never claim "done" for partial work.
- **Quote real output.** Paste the actual test summary / command output, not a
  paraphrase.
- **Keep it scannable.** Tables for files and checklists; short prose elsewhere.
- **One report per work-session.** Don't overwrite a prior day's report — new
  date or new description = new file.
- After writing, tell the user the report path.
