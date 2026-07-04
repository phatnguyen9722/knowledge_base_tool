# Merge Header Apps into Features Panel

**Date:** 04/07/2026  
**Tasks:**
1. Remove the standalone "Header Apps" panel from the Settings modal.
2. Merge the "In Header" toggles directly into the main "Features" panel.
3. Use a clean, aligned 3-column layout (App Info, Enabled Toggle, Header Toggle).
4. Synchronize states so disabling an app globally automatically greys out its header toggle.

---

## 1. HTML Layout Changes

**`templates/base.html`**
- Removed the `🔝 Header Apps` button from the sidebar navigation.
- Deleted the separate `#panel-header-apps` container entirely.
- Upgraded the `#panel-features` container:
  - Added a `.features-col-header` row to label the three columns: **App**, **Enabled**, and **In Header**.
  - Updated the bulk actions row (`.features-bulk-row`) to include two sets of buttons (`All` / `None`) side-by-side for both columns.

---

## 2. CSS Grid Implementation

**`static/style.css`**
- Replaced the flexbox layout for `.feature-row` with a robust **CSS Grid** layout (`grid-template-columns: 1fr 70px 70px`).
- This guarantees perfect vertical alignment between the column headers and every toggle switch across all rows, regardless of how long the app name or description is.
- Added styling for the new column headers and tightened up the margins and padding for the bulk actions row so it looks integrated.

```css
.features-col-header, .feature-row {
  display: grid;
  grid-template-columns: 1fr 70px 70px;
  gap: 1rem;
  align-items: center;
}
```

---

## 3. JavaScript Logic Updates

**`static/app.js`**
- Rewrote `buildFeaturesPanel()` to render two `<label class="toggle-switch">` elements per row instead of one.
- **State management:** The script checks both `_loadFeatures()` and `_loadHeaderApps()`. 
  - If the global feature toggle is `off`, the "In Header" toggle gets `disabled` and `opacity: 0.4`.
  - Added a change listener to the global toggle that automatically forces a re-render of the panel so the header toggle correctly updates its disabled state in real-time.
- Both toggles trigger their respective save functions (`setFeature` and `setHeaderApp`) seamlessly from the same row.
- **Search filtering:** The single search bar now filters the merged list perfectly.
- **Backward compatibility:** Left a stub `function buildHeaderAppsPanel() { buildFeaturesPanel(); }` so that the bulk-action wiring for `header-apps-enable-all` still works without throwing errors.
