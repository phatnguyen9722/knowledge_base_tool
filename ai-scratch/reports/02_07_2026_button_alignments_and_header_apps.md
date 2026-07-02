# Button Height Alignments and Header Apps Panel

**Date:** 02/07/2026
**Tasks:**
1. Fix button height mismatch in Notes app (Edit vs Delete)
2. Fix button height mismatch in Music app (Playlists vs Import .mp3)
3. Build new "Header Apps" panel in Settings
4. Add missing "Posts" button to the topbar
5. Prevent toggling disabled features in Header Apps

---

## 1. Notes App: Button Height Fix

### Issue
The "Edit" button (`<a>`) and "Delete" button (`<button>` inside a `<form>`) had slightly different heights despite identical padding, due to browser default `line-height` and `<form>` block formatting.

### Fix
Grouped them using Flexbox with `align-items: stretch` to force identical heights, and `display: contents` on the form to remove it from the layout tree.

**`static/style.css`**
```css
/* Stretches the children to match the tallest sibling */
.note-actions { display: flex; align-items: stretch; ... }

/* Makes the form invisible to flex layout so <button> is a direct flex child */
.note-actions form { display: contents; }

/* Centres the text inside the button regardless of stretched height */
.note-actions .btn { display: flex; align-items: center; line-height: 1; }
```

---

## 2. Music App: Button Height Fix

### Issue
The "▶ Playlists" button and "+ Import .mp3" form were completely misaligned vertically because one aligned to text baseline and the other was forced to the right via `margin-left: auto`.

### Fix
Reused the robust Flexbox stretching technique from the Notes app.

**`templates/music_list.html`**
- Wrapped both buttons in a new `<div class="head-actions">` container.
- Removed the standalone `.head-action` class from the form.

**`static/style.css`**
- Created the `.head-actions` layout class:
```css
.head-actions { margin-left: auto; align-self: center; display: flex; align-items: stretch; gap: .75rem; }
.head-actions form { display: contents; }
.head-actions .btn { display: flex; align-items: center; line-height: 1; margin: 0; }
```

---

## 3. New Settings Panel: "Header Apps"

### Feature
A new panel allowing users to choose which applications appear in the top navigation bar without disabling the application globally (like the "Features" panel does).

### Implementation
**`templates/base.html`**
- Added inline script inside `<head>` to prevent FOUC by dynamically injecting `[data-header-app="xyz"] { display: none !important }` styles on load.
- Added `data-header-app` attributes to all topbar links.
- Added sidebar navigation button "🔝 Header Apps".
- Cloned the Features panel HTML structure for `#panel-header-apps`.

**`static/app.js`**
- Implemented `_loadHeaderApps`, `_saveHeaderApps`, `setHeaderApp`, and `applyHeaderApps` operating on the `kb-header-apps` `localStorage` key.
- Created `buildHeaderAppsPanel()` to dynamically render the toggles with full search filtering.
- Updated `showSettingsPanel` to lazy-load the new panel.

**`static/style.css`**
- Appended `#header-apps-search-input` to the inherited search bar CSS styles to apply theme colors.

---

## 4. Missing "Posts" Button

### Issue
The "Posts" app did not exist in the topbar HTML, meaning it couldn't be navigated to from the header, nor managed by the new "Header Apps" settings.

### Fix
**`templates/base.html`**
- Inserted `<a class="btn" data-feature-app="posts" data-header-app="posts" href="/posts">...` as the first item in the topbar list.

---

## 5. Header Apps UX: Disabled Feature Logic

### Issue
If an app was globally disabled in the "Features" panel, toggling it in the "Header Apps" panel did nothing (the global CSS rule overrode it), which was confusing.

### Fix
**`static/app.js`**
Updated `buildHeaderAppsPanel()` to explicitly check if an app is globally disabled using `isFeatureEnabled()`. If it is:
1. **Visual Cue:** The row opacity is reduced to `0.5`, and the cursor becomes `not-allowed`.
2. **Action Block:** An event listener is attached to the toggle switch which uses `e.preventDefault()` to stop the checkbox from changing.
3. **Feedback:** Triggers an `alert()` informing the user: `"Please enable the '<App Name>' app in the Features panel first."`
