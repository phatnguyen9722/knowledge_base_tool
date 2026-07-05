# Header App Visibility Logic

**Date:** 05/07/2026  
**Goal:** Reduce UI redundancy and save horizontal space in the top navigation bar by dynamically hiding app links based on the user's current context.

---

## 1. Homepage Logic (Block Overriding)

On the Homepage (`/`), the main content area already displays a prominent grid of all available applications. Repeating these exact same links in the top header is redundant.

**Implementation:**
- In `templates/base.html`, all the header app buttons were wrapped inside a Jinja2 block: `{% block header_apps %}`.
- In `templates/home.html`, this block is overridden with an empty block: `{% block header_apps %}{% endblock %}`.
- **Result:** When the server renders the Homepage, it completely strips the app links out of the top navigation bar while keeping the Logo and Search bar intact.

---

## 2. Active App Logic (Path Matching)

When a user is actively using an application (e.g., browsing their Notes), the shortcut to that exact application in the top navigation bar is unnecessary.

**Implementation:**
- In `templates/base.html`, each individual app link was wrapped in a conditional Jinja2 check that inspects the current request URL path:
  ```html
  {% if not request.url.path.startswith('/notes') %}
    <a class="btn" href="/notes">...</a>
  {% endif %}
  ```
- **Result:** Because we use `.startswith()`, this logic correctly hides the active app's button not just on the main app page (e.g., `/notes`), but also deep within any of its sub-pages or edit screens (e.g., `/notes/new`, `/notes/my-secret-note`). All other app buttons remain fully visible for quick context switching.
