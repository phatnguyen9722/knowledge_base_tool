"""Tests for the Bookmarks feature."""

import pytest
from fastapi.testclient import TestClient

from app.bookmarks import BookmarksManager


# --------------------------------------------------------------------------- #
# Manager
# --------------------------------------------------------------------------- #
@pytest.fixture
def mgr(tmp_path):
    return BookmarksManager(tmp_path / "bookmarks")


def test_create_and_read(mgr):
    slug = mgr.create({
        "title": "GitHub", "url": "https://github.com",
        "tags": ["git", "Code"], "category": "Dev",
        "description": "Code hosting",
    })
    bm = mgr.read(slug)
    assert bm.title == "GitHub"
    assert bm.url == "https://github.com"
    assert bm.tags == ["git", "code"]    # normalised
    assert bm.category == "Dev"
    assert bm.domain == "github.com"
    assert bm.pinned is False


def test_domain_property():
    from app.bookmarks import Bookmark
    bm = Bookmark(slug="x", title="T", url="https://example.com/path?q=1")
    assert bm.domain == "example.com"


def test_toggle_pin(mgr):
    slug = mgr.create({"title": "A", "url": "http://a.com"})
    assert mgr.toggle_pin(slug) is True
    assert mgr.read(slug).pinned is True
    assert mgr.toggle_pin(slug) is False


def test_list_pinned_first(mgr):
    mgr.create({"title": "Old", "url": "http://old.com"})
    mgr.create({"title": "New", "url": "http://new.com"})
    p = mgr.create({"title": "Pinned", "url": "http://pinned.com"})
    mgr.toggle_pin(p)
    titles = [b.title for b in mgr.list()]
    assert titles[0] == "Pinned"


def test_list_filter_tags_and(mgr):
    mgr.create({"title": "Both", "url": "http://a.com", "tags": ["a", "b"]})
    mgr.create({"title": "One",  "url": "http://b.com", "tags": ["a"]})
    assert len(mgr.list(tags=["a"])) == 2
    assert [b.title for b in mgr.list(tags=["a", "b"])] == ["Both"]


def test_list_filter_q(mgr):
    mgr.create({"title": "GitHub", "url": "https://github.com", "description": "git"})
    mgr.create({"title": "YouTube", "url": "https://youtube.com"})
    assert len(mgr.list(q="git")) == 1
    assert mgr.list(q="github.com")[0].title == "GitHub"   # url match


def test_list_filter_category(mgr):
    mgr.create({"title": "A", "url": "http://a.com", "category": "Work"})
    mgr.create({"title": "B", "url": "http://b.com", "category": "Fun"})
    assert len(mgr.list(category="Work")) == 1


def test_all_tags_and_categories(mgr):
    mgr.create({"title": "A", "url": "http://a.com", "tags": ["go", "code"], "category": "Dev"})
    mgr.create({"title": "B", "url": "http://b.com", "tags": ["go"], "category": "Personal"})
    assert mgr.all_tags()["go"] == 2
    assert set(mgr.all_categories()) == {"Dev", "Personal"}


def test_delete(mgr):
    slug = mgr.create({"title": "Temp", "url": "http://t.com"})
    assert mgr.delete(slug) is True
    assert mgr.read(slug) is None


# --------------------------------------------------------------------------- #
# Routes
# --------------------------------------------------------------------------- #
@pytest.fixture
def client(tmp_path, monkeypatch):
    import app.main as m
    from app.post_manager import PostManager
    from app.tag_manager import TagManager

    pm = PostManager(tmp_path / "posts", tmp_path / ".kb" / "search.db")
    bm = BookmarksManager(tmp_path / "bookmarks")
    monkeypatch.setattr(m, "pm", pm)
    monkeypatch.setattr(m, "tm", TagManager(tmp_path / "posts"))
    monkeypatch.setattr(m, "bmarks", bm)
    with TestClient(m.app) as c:
        c.bmarks = bm
        yield c
    pm.search.close()


def test_bookmarks_button_in_topbar(client):
    assert 'href="/bookmarks"' in client.get("/").text


def test_bookmarks_homepage_box(client):
    assert 'data-feature-app="bookmarks"' in client.get("/").text


def test_empty_list(client):
    assert "No bookmarks yet" in client.get("/bookmarks").text


def test_create_shows_on_list(client):
    r = client.post("/bookmarks/new", data={
        "title": "GitHub", "url": "https://github.com",
        "description": "code hosting", "tags": "git,code", "category": "Dev",
    }, follow_redirects=False)
    assert r.status_code == 303
    html = client.get("/bookmarks").text
    assert "GitHub" in html
    assert "github.com" in html
    assert "#git" in html
    assert "Dev" in html


def test_tag_filter(client):
    client.post("/bookmarks/new",
                data={"title": "GH", "url": "http://github.com", "tags": "git"},
                follow_redirects=False)
    client.post("/bookmarks/new",
                data={"title": "YT", "url": "http://youtube.com", "tags": "video"},
                follow_redirects=False)
    html = client.get("/bookmarks", params={"tag": ["git"]}).text
    assert "GH" in html and "YT" not in html


def test_search_filter(client):
    client.post("/bookmarks/new",
                data={"title": "Python Docs", "url": "http://docs.python.org"},
                follow_redirects=False)
    assert "Python Docs" in client.get("/bookmarks", params={"q": "python"}).text


def test_edit_and_pin_and_delete(client):
    client.post("/bookmarks/new",
                data={"title": "Editable", "url": "http://e.com"},
                follow_redirects=False)
    assert client.get("/bookmarks/editable/edit").status_code == 200
    client.post("/bookmarks/editable/edit",
                data={"title": "Edited", "url": "http://e.com"},
                follow_redirects=False)
    assert client.bmarks.read("editable").title == "Edited"
    client.post("/bookmarks/editable/pin", follow_redirects=False)
    assert client.bmarks.read("editable").pinned is True
    r = client.post("/bookmarks/editable/delete", follow_redirects=False)
    assert r.status_code == 303 and client.bmarks.read("editable") is None


def test_404_for_missing(client):
    assert client.get("/bookmarks/ghost/edit").status_code == 404
