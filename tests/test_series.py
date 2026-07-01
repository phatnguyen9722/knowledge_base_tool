"""Tests for the post-series feature (linking posts as a series of topics)."""

import pytest
from fastapi.testclient import TestClient

from app.models import Post
from datetime import date


# --------------------------------------------------------------------------- #
# Model
# --------------------------------------------------------------------------- #
def test_post_series_fields_default_and_set():
    p = Post(slug="s", title="t", created=date(2024, 1, 1), updated=date(2024, 1, 1),
             tags=[], category="G")
    assert p.series == "" and p.series_order == 0

    p2 = Post(slug="s2", title="t2", created=date(2024, 1, 1), updated=date(2024, 1, 1),
              tags=[], category="G", series="Docker 101", series_order=2)
    assert p2.series == "Docker 101" and p2.series_order == 2


# --------------------------------------------------------------------------- #
# PostManager.series()
# --------------------------------------------------------------------------- #
@pytest.fixture
def pm(tmp_path):
    from app.post_manager import PostManager
    m = PostManager(tmp_path / "posts", tmp_path / ".kb" / "search.db")
    yield m
    m.search.close()


def _mk(pm, title, series="", order=0):
    return pm.create({"title": title, "tags": [], "category": "G",
                      "status": "published", "series": series, "series_order": order})


def test_series_returns_ordered_members(pm):
    _mk(pm, "Part Two", series="Docker", order=2)
    _mk(pm, "Part One", series="Docker", order=1)
    _mk(pm, "Part Three", series="Docker", order=3)
    _mk(pm, "Unrelated", series="", order=0)

    members = pm.series("Docker")
    assert [p.title for p in members] == ["Part One", "Part Two", "Part Three"]
    # the unrelated post is not in the series
    assert all(p.series == "Docker" for p in members)


def test_series_empty_name_returns_empty(pm):
    _mk(pm, "Loner")
    assert pm.series("") == []


# --------------------------------------------------------------------------- #
# Detail page integration
# --------------------------------------------------------------------------- #
@pytest.fixture
def client(tmp_path, monkeypatch):
    import app.main as m
    from app.post_manager import PostManager
    from app.tag_manager import TagManager

    posts = tmp_path / "posts"
    pmgr = PostManager(posts, tmp_path / ".kb" / "search.db")
    monkeypatch.setattr(m, "pm", pmgr)
    monkeypatch.setattr(m, "tm", TagManager(posts))
    with TestClient(m.app) as c:
        c.pm = pmgr
        yield c
    pmgr.search.close()


def test_detail_shows_series_box_and_prev_next(client):
    _mk(client.pm, "Intro", series="K8s", order=1)
    _mk(client.pm, "Pods", series="K8s", order=2)
    _mk(client.pm, "Services", series="K8s", order=3)

    html = client.get("/posts/pods").text
    assert "series-box" in html
    assert "Series:" in html and "K8s" in html
    assert "part 2 of 3" in html
    # links to the sibling posts
    assert '/posts/intro' in html
    assert '/posts/services' in html
    # prev/next pager
    assert "series-pager" in html
    assert "Intro" in html and "Services" in html


def test_detail_no_series_box_when_standalone(client):
    _mk(client.pm, "Solo Post")
    html = client.get("/posts/solo-post").text
    assert "series-box" not in html


def test_create_via_form_persists_series(client):
    r = client.post("/new", data={
        "title": "Form Series Post", "content": "x", "tags": "",
        "category": "G", "status": "published",
        "series": "My Series", "series_order": "5",
    }, follow_redirects=False)
    assert r.status_code == 303
    post = client.pm.read("form-series-post")
    assert post.series == "My Series"
    assert post.series_order == 5
