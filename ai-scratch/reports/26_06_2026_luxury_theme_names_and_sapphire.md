# Report — Luxury theme names + Sapphire (dark blue) theme

- **Date:** 2026-06-26
- **Author:** Claude (AI agent)
- **Source:** User request — rename themes with luxury names (e.g. vodka, midnight), and add a dark-blue theme.
- **Status:** ✅ Complete — 57/57 tests passing, verified live.

---

## 1. Objective

Give the existing themes evocative "luxury" names, and add a new **dark-blue**
theme.

## 2. What I did

### Renames + new theme
| Old key | New key | Label | Palette |
|---------|---------|-------|---------|
| light | **vodka** | Vodka | clear/white (`:root` default) |
| dark | **midnight** | Midnight | near-black |
| — | **sapphire** | Sapphire | **NEW deep dark blue** (`#0a1429` bg, `#4f8cff` accent) |
| ocean | **aegean** | Aegean | navy/teal |
| clay | **champagne** | Champagne | warm cream |
| rose | **rose** | Rosé | crimson-rose (key unchanged, label → Rosé) |
| purple | **amethyst** | Amethyst | deep violet |

### Files
| File | Change |
|------|--------|
| `static/style.css` | Renamed `[data-theme]` blocks to the new keys, added `[data-theme="sapphire"]`, renamed `.sw-*` swatches and added `.sw-sapphire`. `:root` is the **Vodka** default. |
| `templates/base.html` | Theme picker rebuilt with the 7 luxury options (Vodka, Midnight, Sapphire, Aegean, Champagne, Rosé, Amethyst). |
| `config.yaml` | `ui.theme: vodka` (was `light`) + documented the valid values. |
| `app/config.py` | Settings default `theme` → `vodka`. |
| `static/app.js` | `currentTheme()` fallback `light` → `vodka` so the default highlights. |
| `tests/test_settings.py` | Updated theme-key and swatch assertions; renamed `test_all_themes_defined_in_css`. |

### Design / decisions
- **Vodka = the default** light palette via `:root`. There's intentionally no
  `[data-theme="vodka"]` block — an unmatched `data-theme` value falls through to
  `:root`, which is exactly the Vodka palette. The default `<html>` now carries
  `data-theme="vodka"` so the Vodka swatch shows as active.
- **Sapphire vs Midnight/Aegean:** Sapphire is a deep *blue* navy (`#0a1429`) with
  a bright blue accent, distinct from Midnight (near-black) and Aegean (teal).
- **`rose` key kept** (only the label changed to "Rosé") to avoid an unnecessary
  key churn; the others were renamed since the request was explicitly to rename.

### Migration note (intentional, minor)
Renaming the `data-theme` keys means a previously saved
`localStorage["kb-theme"]` of `ocean`/`clay`/`dark`/`purple` no longer matches a
palette and falls back to Vodka (`:root`). Users just re-pick once. Acceptable
for this stage; no data is affected (themes are per-browser prefs).

## 3. Tests

| Test | Covers |
|------|--------|
| `test_settings_button_and_theme_options_render` | all 7 new `data-theme-set` keys render |
| `test_all_themes_defined_in_css` | 6 `[data-theme]` palettes (+ Vodka via `:root`) and all 7 `.sw-*` swatches |

**Result:** `57 passed in 0.58s`.

**Live check** (uvicorn :5059):
- default `<html data-theme="vodka">`,
- options = `[vodka, midnight, sapphire, aegean, champagne, rose, amethyst]`,
- `[data-theme="sapphire"]` present in served CSS.

## 4. How to verify (manual)

```bash
.venv/bin/python cli.py serve     # http://127.0.0.1:5050  (reload picks up CSS via ?v=)
# ⚙ Settings → Theme → try Sapphire (dark blue), Champagne, Amethyst, etc.
```

## 5. Next steps / ideas

- More luxury palettes are trivial to add: a `[data-theme="<key>"]` block + a
  `.sw-<key>` swatch + one button. (Ideas: Obsidian, Emerald, Bordeaux, Pearl.)
