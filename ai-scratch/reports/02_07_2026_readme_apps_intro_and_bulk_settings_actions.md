# README Update & Bulk Settings Actions

**Date:** 02/07/2026
**Tasks:**
1. Update `README.md` with an interactive "What's Inside?" app introduction.
2. Add bulk action buttons (Enable All / Disable All / Reset All) to the three app-related settings panels.

---

## 1. README: "What's Inside?" Section

### Implementation
Added a concise, interactive section right after the main introduction in `README.md` to immediately hook users by explaining the 8 core mini-apps.
- Used emojis to make the list visually appealing and recognizable.
- Kept descriptions to a single sentence each.
- Added a quick tip letting users know they can toggle the apps on/off in the Settings.

---

## 2. Bulk Actions in Settings Panels

### Feature
Users needed a faster way to manage apps in the Settings modal without clicking individual toggles one-by-one.

### Implementation

**`templates/base.html`**
Added a `.panel-bulk-actions` container directly below the search bar in three panels:
- **Features Panel:** Added `Enable All` and `Disable All` buttons.
- **Header Apps Panel:** Added `Enable All` and `Disable All` buttons.
- **App Icons Panel:** Added a `Reset All Icons` button (to clear all custom uploaded images and revert to emojis).

**`static/style.css`**
Styled the bulk action container as a flex row with equal-width buttons (`flex: 1`) and appropriate spacing.
```css
.panel-bulk-actions { display: flex; gap: .5rem; margin-bottom: .85rem; }
.panel-bulk-actions .btn { flex: 1; padding: .3rem; font-size: .85rem; justify-content: center; }
```

**`static/app.js`**
Appended a `DOMContentLoaded` event listener to the bottom of the script to wire up the logic:
- `Enable All` passes an empty object `{}` to `_saveFeatures()` / `_saveHeaderApps()` (since apps default to enabled when missing from the disabled list).
- `Disable All` iterates over `FEATURE_LIST`, setting every app to `false`.
- `Reset All Icons` explicitly asks for user confirmation via `confirm()`, then clears the `kb-icons` localStorage object.
- All actions immediately re-trigger their respective `apply...()` and `build...()` functions to instantly update the UI without reloading the page.
- Actions that modify the global Features list also trigger `buildHeaderAppsPanel()` to ensure the Header Apps toggles correctly reflect the new global disabled states (greyed out).
