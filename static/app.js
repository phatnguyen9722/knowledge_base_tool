// Knowledge Base – front-end glue.
// Phase 3: markdown live preview + delete button.
// Phase 4: debounced live search, multi-tag aware, keyboard shortcuts, help.
// + theme switching, copy-to-clipboard code blocks.

// Must be defined BEFORE the IIFE so feature/icon functions can access them.
// Feature list — controls Settings → Features panel toggle order and labels.
var FEATURE_LIST = [
  { app: "posts",     label: "Posts",     desc: "Notes & articles" },
  { app: "series",    label: "Series",    desc: "Multi-part topics" },
  { app: "books",     label: "Books",     desc: "Collections of chapters" },
  { app: "toeic",     label: "TOEIC",     desc: "Practice sets" },
  { app: "music",     label: "Music",     desc: "Tracks & playlists" },
  { app: "notes",     label: "Notes",     desc: "Quick pinnable notes" },
  { app: "api-docs",  label: "API Docs",  desc: "REST API reference" },
  { app: "bookmarks", label: "Bookmarks", desc: "Saved links" },
  { app: "tasks",     label: "Tasks",     desc: "Versioned tasks" },
  { app: "emails",    label: "Email",     desc: "Email templates & composer" },
];

var APP_ICONS_DEFAULT = {
  "posts":     "📝",
  "series":    "📚",
  "books":     "📖",
  "toeic":     "🎧",
  "music":     "🎵",
  "notes":     "🗒️",
  "api-docs":  "📄",
  "bookmarks": "🔖",
  "tasks":     "✅",
  "emails":    "✉️",
};
var APP_LABELS = {
  "posts": "Posts", "series": "Series", "books": "Books",
  "toeic": "TOEIC", "music": "Music", "notes": "Notes",
  "api-docs": "API Docs", "bookmarks": "Bookmarks", "tasks": "Tasks",
  "emails": "Email",
};

(function () {
  "use strict";

  const $ = (sel) => document.querySelector(sel);
  const isTyping = () => {
    const el = document.activeElement;
    return el && /^(INPUT|TEXTAREA|SELECT)$/.test(el.tagName);
  };

  // --- Delete buttons (DELETE /posts/{slug}) -------------------------------
  document.addEventListener("click", function (e) {
    const btn = e.target.closest("[data-delete]");
    if (!btn) return;
    const slug = btn.getAttribute("data-delete");
    if (!confirm("Delete this post? This cannot be undone.")) return;
    fetch("/posts/" + encodeURIComponent(slug), { method: "DELETE" })
      .then((r) => (r.ok ? (window.location.href = "/") : alert("Delete failed (" + r.status + ")")))
      .catch(() => alert("Delete failed (network error)"));
  });

  // --- Debounced live search ----------------------------------------------
  const input = $("#search-input");
  const results = $("#search-results");
  let timer = null;

  function currentFilters() {
    // Preserve active tag/category filters from the page URL in live search.
    const p = new URLSearchParams(window.location.search);
    const parts = [];
    p.getAll("tag").forEach((t) => parts.push("tag=" + encodeURIComponent(t)));
    if (p.get("category")) parts.push("category=" + encodeURIComponent(p.get("category")));
    return parts.join("&");
  }

  function hideResults() {
    if (!results) return;
    results.hidden = true;
    results.innerHTML = "";
    if (input) input.setAttribute("aria-expanded", "false");
  }

  function runSearch(q) {
    if (!results) return;
    if (!q.trim()) return hideResults();
    const extra = currentFilters();
    fetch("/api/search?q=" + encodeURIComponent(q) + (extra ? "&" + extra : ""))
      .then((r) => r.json())
      .then((hits) => {
        if (!hits.length) {
          results.innerHTML = '<div class="sr-empty">No matches</div>';
        } else {
          results.innerHTML = hits
            .slice(0, 12)
            .map(
              (h) =>
                '<a class="sr-item" href="/posts/' +
                encodeURIComponent(h.slug) +
                '"><span class="sr-title">' +
                escapeHtml(h.title) +
                '</span><span class="sr-snippet">' +
                (h.snippet || "") + // snippet already contains <mark> from FTS5
                "</span></a>"
            )
            .join("");
        }
        results.hidden = false;
        input.setAttribute("aria-expanded", "true");
      })
      .catch(hideResults);
  }

  function escapeHtml(s) {
    const d = document.createElement("div");
    d.textContent = s == null ? "" : s;
    return d.innerHTML;
  }

  if (input) {
    input.addEventListener("input", function () {
      clearTimeout(timer);
      const q = input.value;
      timer = setTimeout(() => runSearch(q), 200); // debounce 200ms
    });
    document.addEventListener("click", function (e) {
      if (results && !results.contains(e.target) && e.target !== input) hideResults();
    });
  }

  // --- Settings modal — two-panel (sidebar nav + content) -----------------
  const settingsModal = $("#settings-modal");
  var _activeSettingsPanel = "theme";   // remember last active panel

  function showSettingsPanel(id) {
    _activeSettingsPanel = id;
    // Show/hide content panels
    document.querySelectorAll(".settings-panel").forEach(function (p) {
      p.hidden = p.id !== "panel-" + id;
    });
    // Update sidebar active state
    document.querySelectorAll(".settings-nav-item").forEach(function (btn) {
      btn.classList.toggle("active", btn.getAttribute("data-panel") === id);
    });
    // Lazy-refresh dynamic panels when they become visible
    if (id === "features")     buildFeaturesPanel();
    if (id === "header-apps")  buildHeaderAppsPanel();
    if (id === "app-icons")    buildIconPicker();
    if (id === "icon-library") loadIconLibrary();
    if (id === "background")   loadBgPanel();
  }

  // Wire sidebar nav items
  document.querySelectorAll(".settings-nav-item").forEach(function (btn) {
    btn.addEventListener("click", function () {
      showSettingsPanel(btn.getAttribute("data-panel"));
    });
  });

  function toggleSettings(force) {
    if (!settingsModal) return;
    settingsModal.hidden = force === undefined ? !settingsModal.hidden : !force;
    // When opening: restore last active panel and refresh its content
    if (!settingsModal.hidden) {
      showSettingsPanel(_activeSettingsPanel);
    }
  }

  const settingsBtn = $("#settings-btn");
  const settingsClose = $("#settings-close");
  if (settingsBtn) settingsBtn.addEventListener("click", () => toggleSettings());
  if (settingsClose) settingsClose.addEventListener("click", () => toggleSettings(false));

  function currentTheme() {
    return document.documentElement.getAttribute("data-theme") || "vodka";
  }
  function markActiveTheme() {
    const t = currentTheme();
    document.querySelectorAll("[data-theme-set]").forEach((b) => {
      b.classList.toggle("active", b.getAttribute("data-theme-set") === t);
    });
  }
  function applyTheme(theme) {
    document.documentElement.setAttribute("data-theme", theme);
    try {
      localStorage.setItem("kb-theme", theme);
    } catch (e) {}
    markActiveTheme();
  }
  document.querySelectorAll("[data-theme-set]").forEach((btn) => {
    btn.addEventListener("click", () => applyTheme(btn.getAttribute("data-theme-set")));
  });
  markActiveTheme();

  // --- Theme search (filters .theme-opt buttons by their label text) --------
  (function () {
    var themeInput = document.getElementById("theme-search-input");
    var themeClear = document.getElementById("theme-search-clear");
    if (!themeInput) return;

    function applyThemeSearch() {
      var q = themeInput.value.trim().toLowerCase();
      var anyVisible = false;
      document.querySelectorAll(".theme-opt").forEach(function (btn) {
        // The label is the last <span> child text
        var label = (btn.textContent || "").trim().toLowerCase();
        var match = !q || label.indexOf(q) !== -1;
        btn.style.display = match ? "" : "none";
        if (match) anyVisible = true;
      });
      // Empty state inside the grid
      var grid = document.getElementById("theme-grid");
      if (grid) {
        var empty = grid.querySelector(".theme-empty");
        if (!anyVisible) {
          if (!empty) {
            empty = document.createElement("p");
            empty.className = "theme-empty muted";
            empty.style.cssText = "font-size:.88rem;margin:.5rem 0;grid-column:1/-1";
            grid.appendChild(empty);
          }
          empty.textContent = 'No themes match "' + themeInput.value.trim() + '".';
        } else if (empty) {
          empty.remove();
        }
      }
      if (themeClear) themeClear.hidden = !q;
    }

    themeInput.addEventListener("input",  applyThemeSearch);
    themeInput.addEventListener("search", applyThemeSearch);
    if (themeClear) {
      themeClear.addEventListener("click", function () {
        themeInput.value = "";
        applyThemeSearch();
        themeInput.focus();
      });
    }
  })();


  const helpModal = $("#help-modal");
  function toggleHelp(force) {
    if (!helpModal) return;
    helpModal.hidden = force === undefined ? !helpModal.hidden : !force;
  }
  const helpBtn = $("#help-btn");
  const helpClose = $("#help-close");
  if (helpBtn) helpBtn.addEventListener("click", () => toggleHelp());
  if (helpClose) helpClose.addEventListener("click", () => toggleHelp(false));

  // --- Keyboard shortcuts --------------------------------------------------
  document.addEventListener("keydown", function (e) {
    // Esc always closes overlays.
    if (e.key === "Escape") {
      hideResults();
      toggleHelp(false);
      toggleSettings(false);
      if (input && document.activeElement === input) input.blur();
      return;
    }
    if (isTyping()) return; // don't hijack typing

    if (e.key === "/") {
      e.preventDefault();
      if (input) input.focus();
    } else if (e.key === "n") {
      window.location.href = "/new";
    } else if (e.key === "e") {
      const m = window.location.pathname.match(/^\/posts\/(.+)$/);
      if (m) window.location.href = "/edit/" + m[1];
    } else if (e.key === "?") {
      e.preventDefault();
      toggleHelp();
    }
  });

  // --- Copy buttons on rendered code blocks --------------------------------
  document.querySelectorAll(".markdown").forEach(enhanceCodeBlocks);

  // --- Apply stored preferences on load ------------------------------------
  applyFeatures();     // hide/show sections per stored feature toggles
  applyAppIcons();     // swap emojis for custom icon images

  // Pre-populate static panels so they're ready the first time Settings opens
  buildIconPicker();

  // --- TOEIC: reveal/hide answer + mark correctness ------------------------
  function revealAnswer(q, show) {
    const box = q.querySelector(".answer-box");
    const btn = q.querySelector("[data-answer-toggle]");
    const verdict = q.querySelector(".verdict");
    if (!box) return;
    box.hidden = !show;
    if (btn) btn.textContent = show ? "Hide answer" : "Show answer";
    const correct = q.getAttribute("data-correct");
    q.querySelectorAll(".choice").forEach(function (c) {
      c.classList.toggle("correct", show && c.getAttribute("data-letter") === correct);
    });
    if (verdict) {
      if (!show) {
        verdict.textContent = "";
        verdict.className = "verdict";
      } else {
        const chosen = q.querySelector("input[type=radio]:checked");
        if (!chosen) {
          verdict.textContent = "(no answer selected)";
          verdict.className = "verdict";
        } else if (chosen.value === correct) {
          verdict.textContent = "✓ Correct";
          verdict.className = "verdict ok";
        } else {
          verdict.textContent = "✗ Incorrect (you chose " + chosen.value + ")";
          verdict.className = "verdict bad";
        }
      }
    }
  }

  document.addEventListener("click", function (e) {
    const btn = e.target.closest("[data-answer-toggle]");
    if (!btn) return;
    const q = btn.closest(".toeic-q");
    if (q) revealAnswer(q, q.querySelector(".answer-box").hidden);
  });

  const toggleAll = $("#toeic-toggle-all");
  if (toggleAll) {
    toggleAll.addEventListener("click", function () {
      const qs = document.querySelectorAll(".toeic-q");
      // If any is hidden, show all; otherwise hide all.
      const anyHidden = Array.prototype.some.call(qs, function (q) {
        return q.querySelector(".answer-box").hidden;
      });
      qs.forEach(function (q) { revealAnswer(q, anyHidden); });
      toggleAll.textContent = anyHidden ? "Hide all answers" : "Show all answers";
    });
  }

  // --- Back-to-top button --------------------------------------------------
  const toTop = $("#to-top");
  if (toTop) {
    const sync = function () {
      toTop.classList.toggle("visible", window.scrollY > 300);
    };
    window.addEventListener("scroll", sync, { passive: true });
    sync();
    toTop.addEventListener("click", function () {
      window.scrollTo({ top: 0, behavior: "smooth" });
    });
  }
})();

// --- Editor live preview (marked.js) ---------------------------------------
// Called from editor.html after marked.js loads.
function initEditor() {
  const input = document.getElementById("md-input");
  const preview = document.getElementById("md-preview");
  if (!input || !preview || typeof marked === "undefined") return;
  marked.setOptions({ breaks: true });

  const render = function () {
    preview.innerHTML = marked.parse(input.value || "");
    enhanceCodeBlocks(preview);
  };
  input.addEventListener("input", render);
  render();

  // Paste an image → upload to /img and insert a markdown image link.
  input.addEventListener("paste", function (e) {
    const items = (e.clipboardData && e.clipboardData.items) || [];
    for (let i = 0; i < items.length; i++) {
      if (items[i].kind === "file" && items[i].type.indexOf("image/") === 0) {
        const file = items[i].getAsFile();
        if (file) {
          e.preventDefault();
          uploadImage(file, input, render);
        }
        return;
      }
    }
  });
}

// Upload a pasted/dropped image file and insert its markdown at the cursor.
function uploadImage(file, input, render) {
  const placeholder = "![uploading " + (file.name || "image") + "…]()";
  insertAtCursor(input, placeholder);
  if (render) render();

  const form = new FormData();
  form.append("file", file, file.name || "pasted-image");

  fetch("/api/upload", { method: "POST", body: form })
    .then(function (r) {
      if (!r.ok) throw new Error("HTTP " + r.status);
      return r.json();
    })
    .then(function (data) {
      input.value = input.value.replace(placeholder, data.markdown);
      if (render) render();
    })
    .catch(function (err) {
      input.value = input.value.replace(placeholder, "");
      if (render) render();
      alert("Image upload failed: " + err.message);
    });
}

function insertAtCursor(input, text) {
  const start = input.selectionStart || 0;
  const end = input.selectionEnd || 0;
  input.value = input.value.slice(0, start) + text + input.value.slice(end);
  const pos = start + text.length;
  input.selectionStart = input.selectionEnd = pos;
  input.focus();
}

// --- Playlist "Play all" continuous player ---------------------------------
// Plays the playlist in order, auto-advancing on track end; highlights current.
function initPlaylistPlayer() {
  const root = document.getElementById("play-all");
  const audio = document.getElementById("pa-audio");
  const dataEl = document.getElementById("pa-data");
  const playBtn = document.getElementById("pa-play");
  const now = root && root.querySelector(".pa-now");
  if (!root || !audio || !dataEl) return;

  let tracks = [];
  try { tracks = JSON.parse(dataEl.textContent || "[]"); } catch (e) { return; }
  if (!tracks.length) return;

  let i = -1;

  const highlight = function (slug) {
    document.querySelectorAll(".playlist-tracks > li").forEach(function (li) {
      li.classList.toggle("playing", li.getAttribute("data-slug") === slug);
    });
  };

  const load = function (idx, autoplay) {
    if (idx < 0 || idx >= tracks.length) return;
    i = idx;
    const t = tracks[i];
    audio.src = t.url;
    if (now) now.textContent = "Now playing: " + t.title + "  (" + (i + 1) + "/" + tracks.length + ")";
    highlight(t.slug);
    if (autoplay) audio.play().catch(function () {});
  };

  if (playBtn) {
    playBtn.addEventListener("click", function () { load(0, true); });
  }
  audio.addEventListener("ended", function () {
    if (i + 1 < tracks.length) load(i + 1, true);
    else if (now) now.textContent = "Finished.";
  });
}

// --- Cover image upload (collections) --------------------------------------
// Wires a file input to /api/upload; fills the hidden URL field + preview.
function initCoverUpload() {
  const fileInput = document.querySelector("[data-cover-file]");
  const urlInput = document.getElementById("cover-url");
  const preview = document.getElementById("cover-preview");
  if (!fileInput || !urlInput) return;

  const showPreview = function (url) {
    if (!preview) return;
    if (url) {
      preview.src = url;
      preview.hidden = false;
    } else {
      preview.hidden = true;
    }
  };
  showPreview(urlInput.value);
  urlInput.addEventListener("input", function () { showPreview(urlInput.value); });

  fileInput.addEventListener("change", function () {
    const file = fileInput.files && fileInput.files[0];
    if (!file) return;
    const form = new FormData();
    form.append("file", file, file.name || "cover");
    fileInput.disabled = true;
    fetch("/api/upload", { method: "POST", body: form })
      .then(function (r) {
        if (!r.ok) throw new Error("HTTP " + r.status);
        return r.json();
      })
      .then(function (data) {
        urlInput.value = data.url;
        showPreview(data.url);
      })
      .catch(function (err) { alert("Cover upload failed: " + err.message); })
      .then(function () { fileInput.disabled = false; });
  });
}

// --- Code-block copy buttons -----------------------------------------------
// Wraps each <pre> in a container and adds a hover-reveal "Copy" button.
// ---------------------------------------------------------------------------
// ---------------------------------------------------------------------------
// Feature management — Settings → Features
// ---------------------------------------------------------------------------

function _loadFeatures() {
  try { return JSON.parse(localStorage.getItem("kb-features") || "{}"); } catch (e) { return {}; }
}
function _saveFeatures(f) {
  try { localStorage.setItem("kb-features", JSON.stringify(f)); } catch (e) {}
}

function isFeatureEnabled(app) {
  return _loadFeatures()[app] !== false;   // default: enabled
}

function setFeature(app, enabled) {
  var f = _loadFeatures();
  if (enabled) {
    delete f[app];           // default is on → remove the key entirely
  } else {
    f[app] = false;
  }
  _saveFeatures(f);
  applyFeatures();
}

// Show/hide all [data-feature-app="..."] elements based on stored prefs.
function applyFeatures() {
  var f = _loadFeatures();
  FEATURE_LIST.forEach(function (feat) {
    var hidden = f[feat.app] === false;
    document.querySelectorAll('[data-feature-app="' + feat.app + '"]').forEach(function (el) {
      el.style.display = hidden ? "none" : "";
    });
  });
}

// Render the combined Features + Header Apps panel (two toggle columns per row).
function buildFeaturesPanel() {
  var list = document.getElementById("features-panel-list");
  if (!list) return;
  var f = _loadFeatures();
  var h = _loadHeaderApps();

  list.innerHTML = FEATURE_LIST.map(function (feat) {
    var featEnabled   = f[feat.app] !== false;
    var headerEnabled = h[feat.app] !== false;
    var globalOn      = featEnabled; // header toggle disabled when feature is off

    return '<div class="feature-row"' +
      ' data-label="' + feat.label.toLowerCase() + '"' +
      ' data-desc="'  + (feat.desc || "").toLowerCase() + '"' +
      ' data-app="'   + feat.app + '">' +
      // App name + description
      '<div class="feature-row-info">' +
        '<span class="feature-row-label">' + feat.label + '</span>' +
        (feat.desc ? '<span class="feature-row-desc">' + feat.desc + '</span>' : '') +
      '</div>' +
      // Enabled toggle
      '<label class="toggle-switch">' +
        '<input type="checkbox" data-feature-toggle="' + feat.app + '"' + (featEnabled ? ' checked' : '') + '>' +
        '<span class="toggle-slider"></span>' +
      '</label>' +
      // Header toggle (dimmed + blocked when feature itself is disabled)
      '<label class="toggle-switch"' + (!globalOn ? ' style="opacity:.4;cursor:not-allowed"' : '') + '>' +
        '<input type="checkbox" data-header-toggle="' + feat.app + '"' +
          (headerEnabled ? ' checked' : '') +
          (!globalOn ? ' disabled' : '') + '>' +
        '<span class="toggle-slider"></span>' +
      '</label>' +
    '</div>';
  }).join('');

  // Wire Feature toggles
  list.querySelectorAll("[data-feature-toggle]").forEach(function (cb) {
    cb.addEventListener("change", function () {
      setFeature(cb.getAttribute("data-feature-toggle"), cb.checked);
      // Re-render so the header column's disabled state refreshes
      buildFeaturesPanel();
    });
  });

  // Wire Header toggles
  list.querySelectorAll("[data-header-toggle]").forEach(function (cb) {
    if (cb.disabled) return;
    cb.addEventListener("change", function () {
      setHeaderApp(cb.getAttribute("data-header-toggle"), cb.checked);
    });
  });

  // Shared search
  var searchInput = document.getElementById("features-search-input");
  var clearBtn    = document.getElementById("features-search-clear");
  if (!searchInput) return;

  function applyFeatureSearch() {
    var q = searchInput.value.trim().toLowerCase();
    var anyVisible = false;
    list.querySelectorAll(".feature-row").forEach(function (row) {
      var match = !q ||
        row.getAttribute("data-label").indexOf(q) !== -1 ||
        row.getAttribute("data-desc").indexOf(q)  !== -1;
      row.style.display = match ? "" : "none";
      if (match) anyVisible = true;
    });
    var empty = list.querySelector(".features-empty");
    if (!anyVisible) {
      if (!empty) {
        empty = document.createElement("p");
        empty.className = "features-empty muted";
        empty.style.fontSize = ".88rem";
        empty.style.margin = ".5rem 0";
        list.appendChild(empty);
      }
      empty.textContent = 'No features match "' + searchInput.value.trim() + '".';
    } else if (empty) {
      empty.remove();
    }
    if (clearBtn) clearBtn.hidden = !q;
  }

  if (searchInput._featureSearchHandler) {
    searchInput.removeEventListener("input",  searchInput._featureSearchHandler);
    searchInput.removeEventListener("search", searchInput._featureSearchHandler);
  }
  searchInput._featureSearchHandler = applyFeatureSearch;
  searchInput.addEventListener("input",  applyFeatureSearch);
  searchInput.addEventListener("search", applyFeatureSearch);

  if (clearBtn) {
    if (clearBtn._featureClearHandler) {
      clearBtn.removeEventListener("click", clearBtn._featureClearHandler);
    }
    clearBtn._featureClearHandler = function () {
      searchInput.value = "";
      applyFeatureSearch();
      searchInput.focus();
    };
    clearBtn.addEventListener("click", clearBtn._featureClearHandler);
  }

  applyFeatureSearch();
}

// buildHeaderAppsPanel is kept as an alias so bulk-action wiring stays intact.
function buildHeaderAppsPanel() { buildFeaturesPanel(); }


// ---------------------------------------------------------------------------
// Header Apps management — Settings → Features (merged)
// ---------------------------------------------------------------------------

function _loadHeaderApps() {
  try { return JSON.parse(localStorage.getItem("kb-header-apps") || "{}"); } catch (e) { return {}; }
}
function _saveHeaderApps(h) {
  try { localStorage.setItem("kb-header-apps", JSON.stringify(h)); } catch (e) {}
}

function setHeaderApp(app, enabled) {
  var h = _loadHeaderApps();
  if (enabled) { delete h[app]; } else { h[app] = false; }
  _saveHeaderApps(h);
  applyHeaderApps();
}

// Show/hide [data-header-app="..."] elements based on stored prefs.
function applyHeaderApps() {
  var h = _loadHeaderApps();
  FEATURE_LIST.forEach(function (feat) {
    var hidden = h[feat.app] === false;
    document.querySelectorAll('[data-header-app="' + feat.app + '"]').forEach(function (el) {
      el.style.display = hidden ? "none" : "";
    });
  });
}

// (APP_ICONS_DEFAULT and APP_LABELS are defined at the top of this file)
// ---------------------------------------------------------------------------

function _loadIcons() {
  try { return JSON.parse(localStorage.getItem("kb-icons") || "{}"); } catch (e) { return {}; }
}
function _saveIcons(stored) {
  try { localStorage.setItem("kb-icons", JSON.stringify(stored)); } catch (e) {}
}

// Swap all .app-icon[data-app] spans with the stored custom icon (or restore emoji).
function applyAppIcons() {
  var stored = _loadIcons();
  Object.keys(APP_ICONS_DEFAULT).forEach(function (app) {
    var url = stored[app];
    document.querySelectorAll('.app-icon[data-app="' + app + '"]').forEach(function (el) {
      if (url) {
        el.innerHTML = '<img src="' + url + '" class="app-icon-img" alt="">';
      } else {
        el.textContent = APP_ICONS_DEFAULT[app];
      }
    });
  });
}

function setAppIcon(app, url) {
  var stored = _loadIcons();
  stored[app] = url;
  _saveIcons(stored);
  applyAppIcons();
}

function resetAppIcon(app) {
  var stored = _loadIcons();
  delete stored[app];
  _saveIcons(stored);
  applyAppIcons();
}

// Build the App Icons section inside the settings modal.
// Icon library — paginated (10 per page).
var _iconLibAll = [];   // cached after fetch
var _iconLibPage = 0;
var ICONS_PER_PAGE = 12;

// Fetch all icons from the server, then render page 0.
function loadIconLibrary() {
  var grid = document.getElementById("icon-library");
  if (!grid) return;
  grid.innerHTML = '<span class="muted" style="font-size:.82rem">Loading…</span>';
  fetch("/api/icons")
    .then(function (r) { return r.ok ? r.json() : Promise.reject(r.status); })
    .then(function (icons) {
      _iconLibAll = icons;
      _iconLibPage = 0;
      _renderIconPage();
    })
    .catch(function () {
      grid.innerHTML = '<span class="muted" style="font-size:.82rem">Failed to load library.</span>';
    });
}

// Render a specific page of the cached icon list.
function _renderIconPage() {
  var grid = document.getElementById("icon-library");
  if (!grid) return;

  var total = _iconLibAll.length;
  var totalPages = Math.max(1, Math.ceil(total / ICONS_PER_PAGE));
  _iconLibPage = Math.max(0, Math.min(_iconLibPage, totalPages - 1));

  if (!total) {
    grid.innerHTML = '<p class="muted" style="font-size:.82rem">No icons uploaded yet.</p>';
    return;
  }

  var start = _iconLibPage * ICONS_PER_PAGE;
  var pageItems = _iconLibAll.slice(start, start + ICONS_PER_PAGE);

  // Icon grid
  var iconsHtml = pageItems.map(function (ic) {
    return '<div class="icon-lib-item" data-url="' + ic.url + '" data-filename="' + ic.filename + '">' +
      '<img src="' + ic.url + '" class="icon-lib-thumb" alt="">' +
      '<div class="icon-lib-actions">' +
        '<select class="icon-lib-select" title="Apply to app">' +
          '<option value="">Apply to…</option>' +
          Object.keys(APP_LABELS).map(function (app) {
            return '<option value="' + app + '">' + APP_LABELS[app] + '</option>';
          }).join('') +
        '</select>' +
        '<button type="button" class="btn icon-lib-del" title="Delete">✕</button>' +
      '</div>' +
    '</div>';
  }).join('');

  // Prev / Next pager (only when there's more than one page)
  var pagerHtml = "";
  if (totalPages > 1) {
    pagerHtml = '<div class="icon-lib-pager">' +
      '<button type="button" class="btn" id="icon-lib-prev"' +
        (_iconLibPage <= 0 ? ' disabled' : '') + '>← Prev</button>' +
      '<span class="muted icon-lib-page-info">' +
        (_iconLibPage + 1) + ' / ' + totalPages +
        ' <span style="opacity:.6">(' + total + ' total)</span>' +
      '</span>' +
      '<button type="button" class="btn" id="icon-lib-next"' +
        (_iconLibPage >= totalPages - 1 ? ' disabled' : '') + '>Next →</button>' +
    '</div>';
  } else {
    pagerHtml = '<p class="muted" style="font-size:.82rem;margin:.5rem 0 0">' +
      total + ' icon' + (total === 1 ? '' : 's') + '</p>';
  }

  grid.innerHTML = '<div class="icon-library-grid">' + iconsHtml + '</div>' + pagerHtml;

  // Wire pager buttons
  var prevBtn = document.getElementById("icon-lib-prev");
  var nextBtn = document.getElementById("icon-lib-next");
  if (prevBtn) prevBtn.addEventListener("click", function () {
    _iconLibPage--;
    _renderIconPage();
  });
  if (nextBtn) nextBtn.addEventListener("click", function () {
    _iconLibPage++;
    _renderIconPage();
  });

  // Wire Apply-to dropdowns
  grid.querySelectorAll(".icon-lib-select").forEach(function (sel) {
    sel.addEventListener("change", function () {
      var app = sel.value;
      if (!app) return;
      var url = sel.closest(".icon-lib-item").getAttribute("data-url");
      setAppIcon(app, url);
      sel.value = "";
      buildIconPicker();
    });
  });

  // Wire Delete buttons
  grid.querySelectorAll(".icon-lib-del").forEach(function (btn) {
    btn.addEventListener("click", function () {
      var item = btn.closest(".icon-lib-item");
      var filename = item.getAttribute("data-filename");
      var url = item.getAttribute("data-url");
      if (!confirm("Delete this icon?\n" + filename)) return;
      fetch("/api/icons/" + encodeURIComponent(filename), { method: "DELETE" })
        .then(function (r) {
          if (!r.ok) throw new Error("HTTP " + r.status);
          // Reset any app that was using the deleted icon
          var stored = _loadIcons();
          Object.keys(stored).forEach(function (app) {
            if (stored[app] === url) resetAppIcon(app);
          });
          buildIconPicker();
          loadIconLibrary();   // re-fetch so count + list are accurate
        })
        .catch(function (err) { alert("Delete failed: " + err.message); });
    });
  });
}

function buildIconPicker() {
  var list = document.getElementById("icon-picker-list");
  if (!list) return;
  var stored = _loadIcons();

  list.innerHTML = Object.keys(APP_ICONS_DEFAULT).map(function (app) {
    var defEmoji = APP_ICONS_DEFAULT[app];
    var customUrl = stored[app] || "";
    var previewHtml = customUrl
      ? '<img src="' + customUrl + '" class="app-icon-img icon-preview-img" alt="">'
      : '<span class="icon-preview-emoji">' + defEmoji + '</span>';
    var label = APP_LABELS[app] || app;
    return '<div class="icon-picker-row" data-label="' + label.toLowerCase() + '">' +
      '<div class="icon-picker-current">' + previewHtml + '</div>' +
      '<span class="icon-picker-label">' + label + '</span>' +
      '<label class="btn icon-upload-btn">' +
        'Change' +
        '<input type="file" accept="image/*" hidden data-icon-app="' + app + '">' +
      '</label>' +
      '<button type="button" class="btn" data-icon-reset="' + app + '"' +
        (customUrl ? '' : ' disabled') + '>Reset</button>' +
      '</div>';
  }).join('');

  // Wire upload inputs
  list.querySelectorAll("input[data-icon-app]").forEach(function (input) {
    input.addEventListener("change", function () {
      var app = input.getAttribute("data-icon-app");
      var file = input.files && input.files[0];
      if (!file) return;
      var form = new FormData();
      form.append("file", file, file.name);
      fetch("/api/upload-icon", { method: "POST", body: form })
        .then(function (r) {
          if (!r.ok) throw new Error("HTTP " + r.status);
          return r.json();
        })
        .then(function (data) {
          setAppIcon(app, data.url);
          buildIconPicker();
          loadIconLibrary();   // show the newly uploaded icon in the library
        })
        .catch(function (err) { alert("Icon upload failed: " + err.message); });
    });
  });

  // Wire reset buttons
  list.querySelectorAll("[data-icon-reset]").forEach(function (btn) {
    btn.addEventListener("click", function () {
      var app = btn.getAttribute("data-icon-reset");
      resetAppIcon(app);
      buildIconPicker();
    });
  });

  // --- App Icons search (filters .icon-picker-row by app label) -------------
  var iconsInput = document.getElementById("icons-search-input");
  var iconsClear = document.getElementById("icons-search-clear");
  if (iconsInput) {
    function applyIconSearch() {
      var q = iconsInput.value.trim().toLowerCase();
      var anyVisible = false;
      list.querySelectorAll(".icon-picker-row").forEach(function (row) {
        var label = (row.getAttribute("data-label") || "").toLowerCase();
        var match = !q || label.indexOf(q) !== -1;
        row.style.display = match ? "" : "none";
        if (match) anyVisible = true;
      });
      // Empty state
      var empty = list.querySelector(".icons-empty");
      if (!anyVisible) {
        if (!empty) {
          empty = document.createElement("p");
          empty.className = "icons-empty muted";
          empty.style.cssText = "font-size:.88rem;margin:.5rem 0";
          list.appendChild(empty);
        }
        empty.textContent = 'No apps match "' + iconsInput.value.trim() + '".';
      } else if (empty) {
        empty.remove();
      }
      if (iconsClear) iconsClear.hidden = !q;
    }

    if (iconsInput._iconSearchHandler) {
      iconsInput.removeEventListener("input",  iconsInput._iconSearchHandler);
      iconsInput.removeEventListener("search", iconsInput._iconSearchHandler);
    }
    iconsInput._iconSearchHandler = applyIconSearch;
    iconsInput.addEventListener("input",  applyIconSearch);
    iconsInput.addEventListener("search", applyIconSearch);

    if (iconsClear) {
      if (iconsClear._iconClearHandler)
        iconsClear.removeEventListener("click", iconsClear._iconClearHandler);
      iconsClear._iconClearHandler = function () {
        iconsInput.value = "";
        applyIconSearch();
        iconsInput.focus();
      };
      iconsClear.addEventListener("click", iconsClear._iconClearHandler);
    }

    applyIconSearch();
  }
}

function enhanceCodeBlocks(container) {
  if (!container) return;
  container.querySelectorAll("pre").forEach(function (pre) {
    if (pre.parentElement && pre.parentElement.classList.contains("code-block")) {
      return; // already enhanced
    }
    const wrap = document.createElement("div");
    wrap.className = "code-block";
    pre.parentNode.insertBefore(wrap, pre);
    wrap.appendChild(pre);

    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = "copy-btn";
    btn.textContent = "Copy";
    btn.addEventListener("click", function () {
      const code = pre.querySelector("code") || pre;
      copyToClipboard(code.innerText, btn);
    });
    wrap.appendChild(btn);
  });
}

function copyToClipboard(text, btn) {
  const flash = function () {
    const orig = btn.textContent;
    btn.textContent = "Copied!";
    btn.classList.add("copied");
    setTimeout(function () {
      btn.textContent = orig;
      btn.classList.remove("copied");
    }, 1500);
  };
  if (navigator.clipboard && navigator.clipboard.writeText) {
    navigator.clipboard.writeText(text).then(flash, function () {
      legacyCopy(text, flash);
    });
  } else {
    legacyCopy(text, flash);
  }
}

function legacyCopy(text, done) {
  const ta = document.createElement("textarea");
  ta.value = text;
  ta.style.position = "fixed";
  ta.style.opacity = "0";
  document.body.appendChild(ta);
  ta.focus();
  ta.select();
  try {
    document.execCommand("copy");
    done();
  } catch (e) {
    /* clipboard unavailable */
  }
  document.body.removeChild(ta);
}

document.addEventListener("DOMContentLoaded", function () {
  // --- Bulk Action Buttons (Settings Panels) ---
  const btnFeatEn = document.getElementById("features-enable-all");
  if (btnFeatEn) {
    btnFeatEn.addEventListener("click", function() {
      _saveFeatures({}); // Default is enabled
      applyFeatures();
      buildFeaturesPanel();
      if (typeof buildHeaderAppsPanel === "function") buildHeaderAppsPanel();
    });
  }

  const btnFeatDis = document.getElementById("features-disable-all");
  if (btnFeatDis) {
    btnFeatDis.addEventListener("click", function() {
      var f = {};
      FEATURE_LIST.forEach(function(feat) { f[feat.app] = false; });
      _saveFeatures(f);
      applyFeatures();
      buildFeaturesPanel();
      if (typeof buildHeaderAppsPanel === "function") buildHeaderAppsPanel();
    });
  }

  const btnHeadEn = document.getElementById("header-apps-enable-all");
  if (btnHeadEn) {
    btnHeadEn.addEventListener("click", function() {
      _saveHeaderApps({});
      applyHeaderApps();
      buildHeaderAppsPanel();
    });
  }

  const btnHeadDis = document.getElementById("header-apps-disable-all");
  if (btnHeadDis) {
    btnHeadDis.addEventListener("click", function() {
      var h = {};
      FEATURE_LIST.forEach(function(feat) { h[feat.app] = false; });
      _saveHeaderApps(h);
      applyHeaderApps();
      buildHeaderAppsPanel();
    });
  }

  const btnIconReset = document.getElementById("icons-reset-all");
  if (btnIconReset) {
    btnIconReset.addEventListener("click", function() {
      if (confirm("Reset all app icons to default emojis?")) {
        _saveIcons({});
        applyAppIcons();
        buildIconPicker();
      }
    });
  }
});

// ===========================================================================
// Background Management
// ===========================================================================

// Built-in backgrounds shipped with the app (served from /static/).
// Add more entries here whenever you drop a new file into static/.
var BG_DEFAULTS = [
  { url: "/static/background_1.svg", label: "Background 1" },
];

var _bgAll = null;  // cached list from /api/backgrounds (null = not yet loaded)

function _loadBgPref() {
  try { return JSON.parse(localStorage.getItem("kb-background") || "null"); } catch(e) { return null; }
}

function _saveBgPref(pref) {
  try { localStorage.setItem("kb-background", JSON.stringify(pref)); } catch(e) {}
}

function _applyBg(pref) {
  var root = document.documentElement;
  if (pref && pref.url) {
    root.style.setProperty("--kb-bg-url", "url('" + pref.url + "')");
    root.style.setProperty("--kb-bg-size", pref.size || "cover");
    root.style.setProperty("--kb-bg-opacity", ((pref.opacity != null ? pref.opacity : 100) / 100).toString());
  } else {
    root.style.removeProperty("--kb-bg-url");
    root.style.removeProperty("--kb-bg-size");
    root.style.removeProperty("--kb-bg-opacity");
  }
}

function _uploadBgFile(file) {
  var zone = document.getElementById("bg-dropzone");
  if (zone) zone.classList.add("uploading");
  var form = new FormData();
  form.append("file", file, file.name);
  fetch("/api/upload-background", { method: "POST", body: form })
    .then(function(r) { if (!r.ok) throw new Error("HTTP " + r.status); return r.json(); })
    .then(function(data) {
      var pref = _loadBgPref() || {};
      pref.url = data.url;
      _saveBgPref(pref);
      _applyBg(pref);
      _bgAll = null;  // invalidate cache so gallery re-fetches
      loadBgPanel();
    })
    .catch(function(err) { alert("Background upload failed: " + err.message); })
    .finally(function() { if (zone) zone.classList.remove("uploading"); });
}

function _updateBgControls() {
  var pref = _loadBgPref();
  var hasActive = pref && pref.url;
  var controls = document.getElementById("bg-controls");
  if (controls) controls.hidden = !hasActive;
  if (!hasActive) return;

  var sizeEl  = document.getElementById("bg-size-select");
  var opacEl  = document.getElementById("bg-opacity-range");
  var opacVal = document.getElementById("bg-opacity-val");
  if (sizeEl)  sizeEl.value = pref.size || "cover";
  if (opacEl)  opacEl.value = pref.opacity != null ? pref.opacity : 100;
  if (opacVal) opacVal.textContent = (pref.opacity != null ? pref.opacity : 100) + "%";
}

// Shared helper: build a gallery item HTML string.
function _bgItemHtml(url, filename, isDefault) {
  var pref = _loadBgPref();
  var isActive = pref && pref.url === url;
  var delBtn = isDefault
    ? ""  // no delete button on built-in defaults
    : '<button type="button" class="bg-gallery-del" title="Delete">\u2715</button>';
  return '<div class="bg-gallery-item' + (isActive ? " active" : "") + '"' +
    ' data-url="' + url + '" data-filename="' + (filename || "") + '">' +
    '<img class="bg-gallery-thumb" src="' + url + '" alt="">' +
    '<span class="bg-gallery-badge">Active</span>' +
    delBtn +
    '</div>';
}

// Wire click-to-activate on every item in a given container element.
function _wireBgGalleryItems(container) {
  container.querySelectorAll(".bg-gallery-item").forEach(function(item) {
    item.addEventListener("click", function(e) {
      if (e.target.classList.contains("bg-gallery-del")) return;
      var url = item.getAttribute("data-url");
      var pref = _loadBgPref() || {};
      pref.url = url;
      _saveBgPref(pref);
      _applyBg(pref);
      _updateBgControls();
      // Refresh active badge on BOTH galleries
      _renderBgDefaultsGallery();
      _renderBgUploadsGallery();
    });

    // Delete button (only on uploads)
    var delBtn = item.querySelector(".bg-gallery-del");
    if (delBtn) {
      delBtn.addEventListener("click", function(e) {
        e.stopPropagation();
        var filename = item.getAttribute("data-filename");
        var url      = item.getAttribute("data-url");
        if (!confirm("Delete this background?\n" + filename)) return;
        fetch("/api/backgrounds/" + encodeURIComponent(filename), { method: "DELETE" })
          .then(function(r) { if (!r.ok) throw new Error("HTTP " + r.status); })
          .then(function() {
            var pref = _loadBgPref();
            if (pref && pref.url === url) {
              _saveBgPref(null);
              _applyBg(null);
              _updateBgControls();
              _renderBgDefaultsGallery();
            }
            _bgAll = null;
            _renderBgUploadsGallery();
          })
          .catch(function(err) { alert("Delete failed: " + err.message); });
      });
    }
  });
}

function _renderBgDefaultsGallery() {
  var el = document.getElementById("bg-defaults-gallery");
  if (!el) return;
  el.innerHTML = BG_DEFAULTS.map(function(bg) {
    return _bgItemHtml(bg.url, null, true);
  }).join("");
  _wireBgGalleryItems(el);
}

function _renderBgUploadsGallery() {
  var el = document.getElementById("bg-gallery");
  if (!el) return;

  if (!_bgAll || !_bgAll.length) {
    el.innerHTML = '<p class="bg-gallery-empty">No backgrounds uploaded yet.</p>';
    return;
  }

  el.innerHTML = _bgAll.map(function(bg) {
    return _bgItemHtml(bg.url, bg.filename, false);
  }).join("");
  _wireBgGalleryItems(el);
}

function loadBgPanel() {
  // Restore controls from saved pref immediately
  _updateBgControls();

  // Always render the built-in defaults (they need no API call)
  _renderBgDefaultsGallery();

  // Wire dropzone
  var zone  = document.getElementById("bg-dropzone");
  var input = document.getElementById("bg-upload-input");
  if (zone && !zone._bgWired) {
    zone._bgWired = true;
    zone.addEventListener("click", function(e) {
      if (e.target.tagName === "LABEL" || e.target.tagName === "INPUT") return;
      input && input.click();
    });
    zone.addEventListener("dragover",  function(e) { e.preventDefault(); zone.classList.add("drag-over"); });
    zone.addEventListener("dragleave", function()  { zone.classList.remove("drag-over"); });
    zone.addEventListener("drop", function(e) {
      e.preventDefault();
      zone.classList.remove("drag-over");
      var file = e.dataTransfer && e.dataTransfer.files && e.dataTransfer.files[0];
      if (file) _uploadBgFile(file);
    });
    if (input) {
      input.addEventListener("change", function() {
        var file = input.files && input.files[0];
        if (file) _uploadBgFile(file);
        input.value = "";
      });
    }
  }

  // Wire size selector
  var sizeEl = document.getElementById("bg-size-select");
  if (sizeEl && !sizeEl._bgWired) {
    sizeEl._bgWired = true;
    sizeEl.addEventListener("change", function() {
      var pref = _loadBgPref() || {};
      pref.size = sizeEl.value;
      _saveBgPref(pref);
      _applyBg(pref);
    });
  }

  // Wire opacity slider
  var opacEl  = document.getElementById("bg-opacity-range");
  var opacVal = document.getElementById("bg-opacity-val");
  if (opacEl && !opacEl._bgWired) {
    opacEl._bgWired = true;
    opacEl.addEventListener("input", function() {
      if (opacVal) opacVal.textContent = opacEl.value + "%";
      var pref = _loadBgPref() || {};
      pref.opacity = parseInt(opacEl.value, 10);
      _saveBgPref(pref);
      _applyBg(pref);
    });
  }

  // Wire Remove Background button
  var removeBtn = document.getElementById("bg-use-default");
  if (removeBtn && !removeBtn._bgWired) {
    removeBtn._bgWired = true;
    removeBtn.addEventListener("click", function() {
      _saveBgPref(null);
      _applyBg(null);
      _updateBgControls();
      _renderBgDefaultsGallery();
      _renderBgUploadsGallery();
    });
  }

  // Fetch uploaded gallery (use cache if already loaded)
  var uploadsEl = document.getElementById("bg-gallery");
  if (!uploadsEl) return;
  if (_bgAll !== null) {
    _renderBgUploadsGallery();
    return;
  }
  uploadsEl.innerHTML = '<p class="bg-gallery-empty muted">Loading\u2026</p>';
  fetch("/api/backgrounds")
    .then(function(r) { return r.json(); })
    .then(function(data) {
      _bgAll = data;
      _renderBgUploadsGallery();
    })
    .catch(function() {
      uploadsEl.innerHTML = '<p class="bg-gallery-empty">Failed to load library.</p>';
    });
}
