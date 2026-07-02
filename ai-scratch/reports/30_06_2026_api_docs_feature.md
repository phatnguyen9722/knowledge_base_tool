# Report — API Documentation feature

- **Date:** 2026-06-30
- **Author:** Claude (AI agent)
- **Source:** User request — a feature to document APIs (project, endpoints, params, responses) without executing them.
- **Status:** ✅ Complete — 205/205 tests passing, verified live.

---

## 1. Objective

A personal REST API reference store: create API projects, document their
endpoints (method, path, parameters, responses), and view them in a clean
searchable/filterable UI — no test execution, just documentation.

## 2. What I did

| File | Change |
|------|--------|
| `app/api_docs.py` | **New.** `ApiParam`, `ApiResponse`, `ApiEndpoint`, `ApiProject` dataclasses; `parse_api_project()` block parser; `ApiDocsManager` (create / read / update / delete / list). `list()` has a try/except guard so malformed files never crash the app. |
| `app/config.py` | `api_docs_dir` setting (default `api-docs/`). |
| `app/main.py` | `ApiDocsManager` instance; routes `GET /api-docs`, `GET/POST /api-docs/new`, `GET /api-docs/{slug}`, `GET/POST /api-docs/{slug}/edit`, `POST /api-docs/{slug}/delete`; homepage box. |
| `templates/api_docs_list.html` | Project index — base URL, version, endpoint count, tags. |
| `templates/api_docs_project.html` | Project detail — method/path filter bar, path search, collapsible endpoint cards (param tables, response blocks, copy-URL button). JS filter/search in-page (no reload needed). |
| `templates/api_docs_editor.html` | Textarea editor with project metadata fields + collapsible format guide. |
| `templates/base.html` | **📄 API Docs** topbar button. |
| `static/style.css` | Method badges (GET=green, POST=blue, PUT=orange, PATCH=purple, DELETE=red), param tables, response status badges (2xx/3xx/4xx/5xx), filter bar, endpoint cards. Dark-theme variants for method badges. |
| `api-docs/sonarqube-api.md` | 5 seeded endpoints — search/create projects, get measures, search issues, quality gate status. |
| `api-docs/github-api.md` | 5 seeded endpoints — get repo, list/create issues, list workflow runs, create PR. |

### File format
Each project is one `.md` file. Frontmatter holds project metadata; body holds
free-form notes then `::: endpoint` blocks:

```
::: endpoint
method: POST
path: /users/{id}
title: Update User
description: Updates user data.
auth: Admin token only          ← overrides project-level auth

param: id    | path  | integer | required | User ID
param: name  | body  | string  | optional | New full name
param: email | body  | string  | optional | New email address

response: 200 | Updated
{"id": 1, "name": "Alice Updated"}

response: 404 | Not Found
{"error": "User not found"}
:::
```

`param:` fields: `name | location | type | required/optional | description`
(location = query, body, path, header).

### Bug caught during development
The seeded `github-api.md` had an unquoted `auth:` value containing `Accept: `
(colon-space), which YAML interprets as a nested key-value mapping
(`yaml.scanner.ScannerError`). Fixed by quoting the value. The `ApiDocsManager.list()`
also had a `try/except` guard added so future malformed files are skipped silently
rather than crashing the homepage.

## 3. Tests

`tests/test_api_docs.py` (21) + prior suite (184) = **205 total**.

| Area | Tests |
|------|-------|
| Parser | metadata, notes → HTML, endpoint count, GET/POST fields, response multi-line, param groups, method_class, empty project |
| Manager | create+read, update preserves created, delete, alpha sort |
| Routes | topbar button, empty index, create+view (badges/params/responses/filter), /new not shadowed, edit+delete, 404, seeded files parse |

**Result:** `205 passed in 1.26s`.

**Live check** (uvicorn :5076):
- Homepage: API Docs box present.
- Index: SonarQube + GitHub listed.
- SonarQube project: 5 endpoint cards, GET/POST badges, param tables, response examples, filter bar.
- Editor: skeleton + format guide load.

## 4. How to use

```bash
.venv/bin/python cli.py serve     # restart for the new routes
# 📄 API Docs → + New Project
# Fill: title, base URL, version, auth type, tags, description
# Write ::: endpoint blocks in the textarea (format guide at the bottom)
# Save → click endpoint headers to expand → use the method/path filter
```

Seeded projects in `api-docs/`:
- `sonarqube-api.md` — SonarQube REST API (5 endpoints)
- `github-api.md` — GitHub REST API (5 endpoints)

## 5. YAML safety note

YAML values containing `: ` (colon-space) must be **quoted** or the parser
will treat everything after as a nested key. In the auth/description fields,
wrap in double quotes if the value contains colons:

```yaml
auth: "Bearer token  (header: Authorization)"  ← quoted: safe
auth: Bearer token  (header: Authorization)     ← unquoted: YAML error!
```

## 6. Next steps / ideas

- Import from OpenAPI/Swagger JSON.
- Tag-filter on the project index.
- Copy curl command per endpoint.
