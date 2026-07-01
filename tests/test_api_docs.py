"""Tests for the API Documentation feature."""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.api_docs import ApiDocsManager, parse_api_project


# ── Parser ──────────────────────────────────────────────────────────────────

SAMPLE = """\
---
title: My API
base_url: https://api.example.com/v1
version: "2.0"
description: Example REST API
auth: Bearer token
tags: [web, rest]
created: 2026-06-30
---

Some project **notes** here.

::: endpoint
method: GET
path: /users
title: List Users
description: Returns all users.

param: page  | query | integer | optional | Page number (default 1)
param: limit | query | integer | optional | Items per page

response: 200 | Success
{"data": [{"id": 1}], "total": 100}

response: 401 | Unauthorized
{"error": "Token required"}
:::

::: endpoint
method: POST
path: /users
title: Create User
description: Creates a new user.
auth: Admin token only

param: name  | body | string | required | Full name
param: email | body | string | required | Email address
param: role  | body | string | optional | admin or member

response: 201 | Created
{"id": 42, "name": "Alice"}

response: 400 | Bad Request
{"error": "Email already exists"}

response: 422 | Validation Error
{"errors": {"email": ["invalid format"]}}
:::
"""


def test_parse_project_metadata():
    p = parse_api_project(SAMPLE, "my-api")
    assert p.title == "My API"
    assert p.base_url == "https://api.example.com/v1"
    assert p.version == "2.0"
    assert p.auth == "Bearer token"
    assert "web" in p.tags


def test_parse_notes_rendered_as_markdown():
    p = parse_api_project(SAMPLE, "my-api")
    assert "<strong>notes</strong>" in p.notes_html


def test_parse_endpoints_count():
    p = parse_api_project(SAMPLE, "my-api")
    assert p.endpoint_count == 2


def test_parse_get_endpoint():
    p = parse_api_project(SAMPLE, "my-api")
    ep = p.endpoints[0]
    assert ep.method == "GET"
    assert ep.path == "/users"
    assert ep.title == "List Users"
    assert ep.method_class == "get"
    assert len(ep.params) == 2
    p0 = ep.params[0]
    assert p0.name == "page"
    assert p0.location == "query"
    assert p0.type == "integer"
    assert p0.required is False


def test_parse_post_endpoint_responses():
    p = parse_api_project(SAMPLE, "my-api")
    ep = p.endpoints[1]
    assert ep.method == "POST"
    assert ep.auth == "Admin token only"
    assert len(ep.params) == 3
    assert ep.params[0].required is True    # name = required
    assert ep.params[2].required is False   # role = optional
    assert len(ep.responses) == 3
    r201 = ep.responses[0]
    assert r201.status == 201
    assert r201.description == "Created"
    assert '"id": 42' in r201.example


def test_parse_response_example_multiline():
    p = parse_api_project(SAMPLE, "my-api")
    r200 = p.endpoints[0].responses[0]
    assert '"data"' in r200.example
    assert r200.example.strip().startswith("{")


def test_param_groups():
    p = parse_api_project(SAMPLE, "my-api")
    ep = p.endpoints[1]
    groups = ep.param_groups
    assert "body" in groups
    assert len(groups["body"]) == 3


def test_method_class_mapping():
    p = parse_api_project(
        "---\ntitle: T\n---\n::: endpoint\nmethod: DELETE\npath: /x\n:::", "t"
    )
    assert p.endpoints[0].method_class == "delete"


def test_empty_project():
    p = parse_api_project("---\ntitle: Empty\n---\n", "empty")
    assert p.endpoint_count == 0
    assert p.notes_html == ""


# ── Manager ─────────────────────────────────────────────────────────────────

@pytest.fixture
def mgr(tmp_path):
    return ApiDocsManager(tmp_path / "api-docs")


def test_create_and_read(mgr):
    slug = mgr.create({
        "title": "Test API", "base_url": "http://api.test", "version": "1.0",
        "content": "::: endpoint\nmethod: GET\npath: /x\n:::\n",
    })
    p = mgr.read(slug)
    assert p.title == "Test API"
    assert p.endpoint_count == 1


def test_update_preserves_created(mgr):
    slug = mgr.create({"title": "API"})
    created = mgr.read(slug).created
    mgr.update(slug, {"title": "API v2", "description": "updated"})
    p = mgr.read(slug)
    assert p.title == "API v2"
    assert p.created == created


def test_delete(mgr):
    slug = mgr.create({"title": "Temp"})
    assert mgr.delete(slug) is True
    assert mgr.read(slug) is None
    assert mgr.delete(slug) is False


def test_list_sorted_alphabetically(mgr):
    mgr.create({"title": "Zebra API"})
    mgr.create({"title": "Alpha API"})
    mgr.create({"title": "Middle API"})
    titles = [p.title for p in mgr.list()]
    assert titles == ["Alpha API", "Middle API", "Zebra API"]


# ── Routes ──────────────────────────────────────────────────────────────────

@pytest.fixture
def client(tmp_path, monkeypatch):
    import app.main as m
    from app.post_manager import PostManager
    from app.tag_manager import TagManager

    pm = PostManager(tmp_path / "posts", tmp_path / ".kb" / "search.db")
    am = ApiDocsManager(tmp_path / "api-docs")
    monkeypatch.setattr(m, "pm", pm)
    monkeypatch.setattr(m, "tm", TagManager(tmp_path / "posts"))
    monkeypatch.setattr(m, "api_docs", am)
    with TestClient(m.app) as c:
        c.api_docs = am
        yield c
    pm.search.close()


def test_api_docs_button_in_topbar(client):
    assert 'href="/api-docs"' in client.get("/").text


def test_api_docs_index_empty(client):
    assert "No API projects" in client.get("/api-docs").text


def test_create_and_view_project(client):
    r = client.post("/api-docs/new", data={
        "title": "Test API", "base_url": "http://api.test",
        "version": "1.0", "auth": "Bearer", "tags": "test",
        "description": "A test API",
        "content": SAMPLE.split("---")[-1],
    }, follow_redirects=False)
    assert r.status_code == 303
    slug = r.headers["location"].split("/")[-1]

    detail = client.get(f"/api-docs/{slug}").text
    assert "Test API" in detail
    assert "method-get" in detail       # GET badge
    assert "method-post" in detail      # POST badge
    assert "api-param-table" in detail  # params table
    assert "api-resp-example" in detail # response examples
    assert "api-filter-bar" in detail   # filter/search


def test_new_not_shadowed(client):
    assert client.get("/api-docs/new").status_code == 200
    assert "<form" in client.get("/api-docs/new").text


def test_edit_and_delete(client):
    client.post("/api-docs/new", data={"title": "Editable"}, follow_redirects=False)
    assert client.get("/api-docs/editable/edit").status_code == 200
    client.post("/api-docs/editable/edit",
                data={"title": "Renamed"}, follow_redirects=False)
    assert client.api_docs.read("editable").title == "Renamed"
    r = client.post("/api-docs/editable/delete", follow_redirects=False)
    assert r.status_code == 303 and client.api_docs.read("editable") is None


def test_404_for_missing(client):
    assert client.get("/api-docs/ghost").status_code == 404


def test_seeded_files_parse():
    """All seeded api-docs files must parse without error."""
    for f in Path("api-docs").glob("*.md"):
        p = parse_api_project(f.read_text(encoding="utf-8"), f.stem)
        assert p.title and p.endpoint_count > 0
