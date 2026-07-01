"""Phase 3 API smoke tests using FastAPI's TestClient.

The app instantiates its PostManager/TagManager at import time against the
configured paths; we monkeypatch them to isolated temp dirs per test.
"""

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client(tmp_path, monkeypatch):
    import app.main as m
    from app.post_manager import PostManager
    from app.tag_manager import TagManager

    posts = tmp_path / "posts"
    pm = PostManager(posts, tmp_path / ".kb" / "search.db")
    monkeypatch.setattr(m, "pm", pm)
    monkeypatch.setattr(m, "tm", TagManager(posts))
    with TestClient(m.app) as c:
        yield c
    pm.search.close()


def _create(client, title="Hello World", **over):
    data = {
        "title": title,
        "content": "# Heading\n\nSome **bold** text.",
        "tags": "docker, devops",
        "category": "DevOps",
        "status": "published",
    }
    data.update(over)
    r = client.post("/new", data=data, follow_redirects=False)
    assert r.status_code == 303, r.text
    return r.headers["location"]  # /posts/{slug}


def test_empty_home_renders(client):
    r = client.get("/posts")
    assert r.status_code == 200
    assert "Knowledge Base" in r.text
    assert "Write your first post" in r.text


def test_create_redirects_and_detail_renders(client):
    loc = _create(client)
    assert loc == "/posts/hello-world"

    r = client.get(loc)
    assert r.status_code == 200
    assert "Hello World" in r.text
    # markdown rendered server-side (headings carry TOC anchor ids)
    assert "<strong>bold</strong>" in r.text
    assert '<h1 id="heading">Heading</h1>' in r.text


def test_home_lists_created_post(client):
    _create(client, title="Listed Post")
    r = client.get("/posts")
    assert r.status_code == 200
    assert "Listed Post" in r.text
    assert "#docker" in r.text


def test_edit_form_and_update(client):
    loc = _create(client, title="Editable")
    slug = loc.rsplit("/", 1)[-1]

    r = client.get(f"/edit/{slug}")
    assert r.status_code == 200
    assert "Editable" in r.text

    r = client.post(
        f"/edit/{slug}",
        data={
            "title": "Editable",
            "content": "updated body",
            "tags": "k8s",
            "category": "Ops",
            "status": "draft",
        },
        follow_redirects=False,
    )
    assert r.status_code == 303

    detail = client.get(loc)
    assert "updated body" in detail.text
    assert "draft" in detail.text


def test_delete_then_404(client):
    loc = _create(client, title="Temp")
    slug = loc.rsplit("/", 1)[-1]

    r = client.delete(f"/posts/{slug}")
    assert r.status_code == 200 and r.json() == {"ok": True}

    assert client.get(loc).status_code == 404
    assert client.delete(f"/posts/{slug}").status_code == 404


def test_api_search_returns_snippet(client):
    _create(client, title="Searchable", content="the unique keyword lives here")
    r = client.get("/api/search", params={"q": "keyword"})
    assert r.status_code == 200
    hits = r.json()
    assert hits and hits[0]["slug"] == "searchable"
    assert "<mark>" in hits[0]["snippet"]
    # content excluded from the JSON payload
    assert "content" not in hits[0]


def test_detail_404_for_missing(client):
    assert client.get("/posts/nope").status_code == 404


def test_new_form_renders(client):
    r = client.get("/new")
    assert r.status_code == 200
    assert "Write markdown here" in r.text
