"""Phase 4 tests: multi-tag AND filter, category facet, search engine tags list.

Covers the backend support for the Search UI & Tag browser:
  - multi-tag AND logic (search + browse)
  - category filtering
  - URL-encoded multi-tag state round-trips through the list route
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
        c.pm = pm
        yield c
    pm.search.close()


def _mk(pm, title, tags, category="General", content="body text"):
    return pm.create({
        "title": title, "tags": tags, "category": category,
        "status": "published", "content": content,
    })


# --------------------------------------------------------------------------- #
# SearchEngine: multi-tag AND
# --------------------------------------------------------------------------- #
def test_search_engine_multi_tag_and(client):
    pm = client.pm
    _mk(pm, "Both", ["docker", "devops"], content="alpha keyword")
    _mk(pm, "OnlyDocker", ["docker"], content="alpha keyword")

    # single tag -> both match
    assert set(pm.search.search("alpha", tags=["docker"])) == {"both", "onlydocker"}
    # AND of two tags -> only the post carrying both
    assert pm.search.search("alpha", tags=["docker", "devops"]) == ["both"]


def test_search_engine_category_filter(client):
    pm = client.pm
    _mk(pm, "Ops Post", ["x"], category="Ops", content="shared term")
    _mk(pm, "Dev Post", ["x"], category="Dev", content="shared term")
    assert pm.search.search("shared", category="Ops") == ["ops-post"]


# --------------------------------------------------------------------------- #
# List route: multi-tag AND browsing
# --------------------------------------------------------------------------- #
def test_list_route_multi_tag_and(client):
    pm = client.pm
    _mk(pm, "Both Tags", ["docker", "devops"])
    _mk(pm, "Single Tag", ["docker"])

    # one tag -> both listed
    r = client.get("/posts", params={"tag": ["docker"]})
    assert "Both Tags" in r.text and "Single Tag" in r.text

    # two tags AND -> only the post with both
    r = client.get("/posts", params={"tag": ["docker", "devops"]})
    assert "Both Tags" in r.text
    assert "Single Tag" not in r.text
    assert "all tags (AND)" in r.text


def test_list_route_category_filter(client):
    pm = client.pm
    _mk(pm, "In Ops", ["a"], category="Ops")
    _mk(pm, "In Dev", ["a"], category="Dev")

    r = client.get("/posts", params={"category": "Ops"})
    assert "In Ops" in r.text
    assert "In Dev" not in r.text
    # category chip rendered with active state
    assert "chip active" in r.text


def test_list_route_renders_facets(client):
    pm = client.pm
    _mk(pm, "P", ["docker"], category="DevOps")
    r = client.get("/posts")
    assert "tag-cloud" in r.text
    assert "#docker" in r.text
    assert "DevOps" in r.text          # category chip
    assert "Status" in r.text          # status facet header


# --------------------------------------------------------------------------- #
# API search honours multiple tags
# --------------------------------------------------------------------------- #
def test_api_search_multi_tag_and(client):
    pm = client.pm
    _mk(pm, "Match", ["docker", "devops"], content="needle here")
    _mk(pm, "NoMatch", ["docker"], content="needle here")

    r = client.get("/api/search", params={"q": "needle", "tag": ["docker", "devops"]})
    hits = r.json()
    assert [h["slug"] for h in hits] == ["match"]
