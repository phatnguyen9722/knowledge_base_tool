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
};
var APP_LABELS = {
  "posts": "Posts", "series": "Series", "books": "Books",
  "toeic": "TOEIC", "music": "Music", "notes": "Notes",
  "api-docs": "API Docs", "bookmarks": "Bookmarks",
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
    if (id === "app-icons")    buildIconPicker();
    if (id === "icon-library") loadIconLibrary();
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

  // --- Help modal ----------------------------------------------------------
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

// Render the toggle-switch list in the Features panel.
function buildFeaturesPanel() {
  var list = document.getElementById("features-panel-list");
  if (!list) return;
  var f = _loadFeatures();
  list.innerHTML = FEATURE_LIST.map(function (feat) {
    var enabled = f[feat.app] !== false;
    return '<div class="feature-row">' +
      '<span class="feature-row-label">' + feat.label + '</span>' +
      '<label class="toggle-switch">' +
        '<input type="checkbox" data-feature-toggle="' + feat.app + '"' + (enabled ? ' checked' : '') + '>' +
        '<span class="toggle-slider"></span>' +
      '</label>' +
    '</div>';
  }).join('');

  list.querySelectorAll("[data-feature-toggle]").forEach(function (cb) {
    cb.addEventListener("change", function () {
      setFeature(cb.getAttribute("data-feature-toggle"), cb.checked);
    });
  });
}

// App icon management — Settings → Modify App
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
    return '<div class="icon-picker-row">' +
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
