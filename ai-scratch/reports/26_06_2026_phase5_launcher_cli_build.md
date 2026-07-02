# Report — Phase 5: Launcher, CLI & Build

- **Date:** 2026-06-26
- **Author:** Claude (AI agent)
- **Source spec:** `requirements.md` → Execution plan, Phase 5
- **Status:** ✅ Code complete — 36/36 tests passing, CLI verified live. ⚠️ Two checklist items (tray launcher run, bundle-on-Python-less-machine) are **not runnable in this headless environment** — see §4.

---

## 1. Objective

Deliver Phase 5: package the app for end users — desktop tray launcher, Typer
CLI, static-site exporter, plugin hook system, and PyInstaller build scripts.

## 2. What I did

| File | Purpose |
|------|---------|
| `app/config.py` | **New** shared `Settings` loader (base-dir + `config.yaml`, bundle-aware). `app/main.py` refactored to use it; `cli.py`, `exporter.py`, `launcher.py` all share it. |
| `app/hooks.py` | Plugin event system: `@on(event)`, `emit()`, `clear()`. Validates event names; isolates handler exceptions. |
| `app/exporter.py` | Static HTML export → `dist/site/` (index + per-post pages, relative links, `style.css` copied). Self-contained (no FastAPI/request dependency). |
| `cli.py` | Typer CLI: `new` / `list` / `search` / `serve` / `build-index` / `export`. |
| `launcher.py` | pystray tray icon + Uvicorn background thread + auto-open browser; bundle-aware icon path. |
| `static/icon.png` | 64×64 tray icon generated with Pillow (blue rounded square + book glyph). |
| `build.sh` / `build.bat` | PyInstaller one-file `--noconsole` builds for macOS/Linux and Windows. |
| `tests/test_phase5.py` | 5 tests: hooks, exporter, CLI round-trip. |

### Wiring
- `PostManager.create/update/delete` now `emit()` `on_post_created` /
  `on_post_updated` / `on_post_deleted`.

### Design decisions / deviations
- **`app/config.py` introduced** (not in spec) to remove the duplicated path/
  config logic the spec had in both `main.py` and `cli.py`. Single source of truth.
- **Exporter uses its own inline template**, not the Jinja app templates — those
  rely on absolute routes (`/posts/{slug}`) and a request object; a static site
  needs relative links (`{slug}.html`). Markdown is rendered with the same
  mistune config as the web app for consistency.
- **`export` added as a CLI command** (spec listed it only as `app/exporter.py`).
- **CLI `new` defaults to `draft`** (matches spec intent for capturing drafts);
  `serve` uses the import-string form so `--reload` works.
- **Hooks swallow handler exceptions** so a broken plugin can't break a save.

## 3. Tests

`tests/test_phase5.py` (5) + Phases 1–4 (31) = **36 total**.

| Phase 5 test | Covers |
|--------------|--------|
| `test_hooks_fire_in_order` | create/update/delete emit correct events |
| `test_on_unknown_event_raises` | event-name validation |
| `test_emit_isolates_handler_errors` | a throwing handler doesn't propagate |
| `test_export_site_published_only` | index + post HTML, drafts excluded, markdown rendered, css copied, relative links |
| `test_cli_round_trip` | `new` → `list` → `search` → `build-index` → `export` |

**Result:** `36 passed in 0.46s` (Python 3.9.6).

**Live checks:**
- `python cli.py --help` lists all 6 commands. ✓
- `launcher.py` byte-compiles (`py_compile`) — not imported/run because the tray
  backend needs a display. ✓

## 4. What could NOT be verified here (be explicit)

- **Tray launcher running** (`launcher.py` → `pystray.Icon(...).run()`): requires
  a GUI session and `pystray` + a platform backend (pyobjc on macOS). Verified by
  syntax-compile only.
- **PyInstaller bundle / "test on a machine without Python"**: building the
  `--onefile` binary and running it on a Python-less machine cannot be done in
  this environment. Scripts are written per the spec but **unbuilt/untested**.

Manual verification steps are in §6.

## 5. Phase 5 checklist status

- [x] `launcher.py` – pystray + webbrowser + uvicorn thread *(written; run not verified — needs display)*
- [x] `static/icon.png` – 64×64 tray icon *(generated with Pillow)*
- [x] `cli.py` – Typer: new / list / search / serve / build-index *(+ export)*
- [x] `app/exporter.py` – export HTML static site to dist/
- [x] PyInstaller build script (macOS + Windows) *(written; build not run here)*
- [x] `app/hooks.py` – plugin event system *(+ wired into PostManager)*
- [ ] **Test bundle on a machine without Python** — **NOT done** (out of scope for this environment; requires building + a clean machine)

## 6. How to verify (manual)

```bash
# CLI
.venv/bin/python cli.py new "My First Note" --tags docker,ops --status published
.venv/bin/python cli.py list
.venv/bin/python cli.py search docker
.venv/bin/python cli.py build-index
.venv/bin/python cli.py export --out dist/site && open dist/site/index.html

# Tray launcher (GUI session; needs pystray + pillow installed)
.venv/bin/pip install pystray pillow
.venv/bin/python launcher.py     # tray icon appears, browser opens

# Standalone build
./build.sh            # macOS/Linux  -> dist/kb-tool
build.bat             # Windows      -> dist\kb-tool.exe
# then copy the binary to a machine without Python and run it.
```

## 7. Project status

All five phases are code-complete. The app runs in the browser (Phase 3
milestone), has full search/tag UX (Phase 4), and a CLI + exporter + tray
launcher + build scripts (Phase 5). **Remaining real-world task:** produce and
smoke-test the PyInstaller bundle on a clean machine (the one unchecked item).
