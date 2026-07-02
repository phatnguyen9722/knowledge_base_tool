# Settings Search Bars + Reverie Theme

**Date:** 02/07/2026
**Tasks:**
1. Add search bar to Settings → Features panel
2. Fix settings modal completely broken after search bar addition
3. Fix search bar filtering not working (rows not hiding)
4. Add search bar to Settings → Theme panel
5. Add search bar to Settings → App Icons panel
6. Fix missing CSS colours on new search bars
7. Add Reverie gradient theme

---

## 1. Settings → Features Search Bar

### Files Changed

#### `templates/base.html`
- Added a `<div class="features-search-wrap">` block above `#features-panel-list` inside the Features panel, containing:
  - A 🔍 icon prefix (`<span class="features-search-icon">`)
  - An `<input type="search" id="features-search-input">`
  - A `✕` clear button (`#features-search-clear`, hidden by default)

#### `static/app.js` — `buildFeaturesPanel()`
- Each `.feature-row` now renders with `data-label` and `data-desc` attributes for matching
- Each row now shows a **description sub-line** (e.g. *"Notes & articles"* under *Posts*)
- Search input filters rows instantly on every keystroke (label + description, case-insensitive)
- Empty-state `<p>` shown when no rows match
- Named handler pattern (`_featureSearchHandler` on the element) prevents listener duplication on re-open

#### `static/style.css`
- Added `.feature-row-info`, `.feature-row-desc` for the new two-line row layout
- Added `.features-search-wrap`, `.features-search-icon`, `#features-search-input`, `#features-search-input::placeholder`, `.features-search-clear` — all using CSS token variables

---

## 2. Bug Fix — Settings Modal Completely Broken

### Root Cause
The empty-state string contained **Unicode smart/curly quotes** (`"` `"`) written literally into the JS source, causing a **syntax parse error** that prevented `app.js` from loading entirely. This broke the whole Settings modal.

### Fix (`static/app.js`)
```js
// Before (broken — curly quotes caused parse error)
empty.textContent = "No features match "" + q + "".";

// After (fixed — plain ASCII quotes in single-quoted string)
empty.textContent = 'No features match "' + q + '".';
```

Additionally, the `cloneNode(true)` approach for deduplicating event listeners was replaced with a cleaner **named handler + `removeEventListener`** pattern (storing the handler on the element itself as `el._featureSearchHandler`).

---

## 3. Bug Fix — Search Bar Types but Nothing Happens

### Root Cause
CSS specificity: `.feature-row { display: flex; … }` **overrides** the browser's built-in `[hidden] { display: none }` rule. Setting `row.hidden = true` toggled the HTML attribute but the flex layout kept rows fully visible.

### Fix (`static/app.js`)
```js
// Before (broken — [hidden] overridden by display:flex)
row.hidden = !match;

// After (fixed — inline style always wins over class rules)
row.style.display = match ? "" : "none";
```
Same fix applied to all subsequent search bars (Theme, App Icons).

---

## 4. Settings → Theme Search Bar

### Files Changed

#### `templates/base.html`
- Added `id="theme-grid"` to the theme grid `<div>` (needed to append the empty-state message)
- Added a `🔍` search bar (`#theme-search-input` + `#theme-search-clear`) above the grid, reusing `.features-search-wrap` styles

#### `static/app.js`
- Added a self-contained **IIFE** wired once at page load (right after `markActiveTheme()`)
- Filters `.theme-opt` buttons by their visible text label
- Empty-state `<p>` uses `grid-column: 1 / -1` to span the full 2-column grid
- Clear button resets filter and re-focuses input

---

## 5. Settings → App Icons Search Bar

### Files Changed

#### `templates/base.html`
- Added a `🔍` search bar (`#icons-search-input` + `#icons-search-clear`) above `#icon-picker-list`, reusing `.features-search-wrap` styles

#### `static/app.js` — `buildIconPicker()`
- Each `.icon-picker-row` now renders with `data-label="<app name lowercase>"` for matching
- Search filter wired at the end of `buildIconPicker()` using the same named-handler pattern (`_iconSearchHandler`, `_iconClearHandler`) so rebuilds don't stack listeners
- Empty-state message shown when no rows match

---

## 6. Bug Fix — Missing CSS Colours on Theme & App Icons Search Bars

### Root Cause
The input colour rules were scoped only to `#features-search-input`. The two new inputs (`#theme-search-input`, `#icons-search-input`) fell back to browser defaults, rendering with wrong text/placeholder colours across all themes.

### Fix (`static/style.css`)
Extended the two ID-scoped selectors to cover all three inputs:
```css
/* Before */
#features-search-input { … color: var(--fg); … }
#features-search-input::placeholder { color: var(--muted); }

/* After */
#features-search-input,
#theme-search-input,
#icons-search-input { … color: var(--fg); … }

#features-search-input::placeholder,
#theme-search-input::placeholder,
#icons-search-input::placeholder { color: var(--muted); }
```

---

## 7. Reverie Gradient Theme

**Name:** *Reverie* — a state of dreamy, romantic contemplation.
**Palette:** `#3a1c71` (deep violet) → `#d76d77` (rose) → `#ffaf7b` (warm peach)

### Design Approach
A two-layer system keeps gradient and solid components compatible:

| Layer | Rule | Purpose |
|---|---|---|
| `--bg: #2d1255` | CSS variable | Topbar, cards, inputs — solid dark plum |
| `[data-theme="reverie"] body { background: linear-gradient(to right, …) }` | Body override | Full-viewport gradient behind solid components |

`background-attachment: fixed` pins the gradient to the viewport so it doesn't scroll with content.

### Colour Tokens

| Token | Value | Role |
|---|---|---|
| `--bg` | `#2d1255` | Solid component backgrounds |
| `--fg` | `#fdf0f5` | Warm near-white text |
| `--muted` | `#c9899a` | Secondary / placeholder text |
| `--border` | `#5e2d6e` | Borders & dividers |
| `--card` | `#3a1a62` | Card surfaces |
| `--accent` | `#ffaf7b` | Links, buttons, active states |
| `--accent-fg` | `#3a1c71` | Text on accent backgrounds |
| `--danger` | `#ff6b8a` | Errors, delete actions |
| `--mark` | `#7a2d50` | `<mark>` highlight |

### Files Changed

#### `static/style.css`
- Added `[data-theme="reverie"]` CSS variable block
- Added `[data-theme="reverie"] body` gradient rule with `background-attachment: fixed`
- Added dark method badge overrides (GET/POST/PUT/PATCH/DELETE) for dark card background
- Added `.sw-reverie` swatch using the full tri-stop gradient (not diagonal split)

#### `templates/base.html`
- Added Reverie picker button after Dracula in the theme grid

#### `tests/test_settings.py`
- Added `"reverie"` to both theme and swatch assertion lists

---

## Summary Table

| # | Change | Files |
|---|---|---|
| 1 | Features search bar | `base.html`, `app.js`, `style.css` |
| 2 | Fix: JS parse error broke all Settings | `app.js` |
| 3 | Fix: `[hidden]` overridden by `display:flex` | `app.js` |
| 4 | Theme search bar | `base.html`, `app.js` |
| 5 | App Icons search bar | `base.html`, `app.js` |
| 6 | Fix: missing CSS colours on new search inputs | `style.css` |
| 7 | Reverie gradient theme | `style.css`, `base.html`, `test_settings.py` |
