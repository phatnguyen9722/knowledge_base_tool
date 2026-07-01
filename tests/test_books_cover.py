"""Tests for Books collection cover, tags, and date + the edit flow."""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.books import BookManager


# --------------------------------------------------------------------------- #
# Manager: cover + tags + dates
# --------------------------------------------------------------------------- #
@pytest.fixture
def mgr(tmp_path):
    return BookManager(tmp_path / "books")


def test_create_with_cover_and_tags(mgr):
    slug = mgr.create_collection({
        "title": "Harry Potter", "author": "JKR",
        "cover": "/img/hp.png", "tags": ["Fantasy", "MAGIC"],
    })
    c = mgr.read_collection(slug)
    assert c.cover == "/img/hp.png"
    assert c.tags == ["fantasy", "magic"]   # normalized
    assert c.created  # date stamped


def test_update_collection_adds_cover_preserves_created(mgr):
    slug = mgr.create_collection({"title": "Dune"})
    created = mgr.read_collection(slug).created
    assert mgr.read_collection(slug).cover == ""

    mgr.update_collection(slug, {"title": "Dune", "cover": "/img/dune.png",
                                 "tags": ["scifi"]})
    c = mgr.read_collection(slug)
    assert c.cover == "/img/dune.png"
    assert c.tags == ["scifi"]
    assert c.created == created            # created preserved
    assert c.chapter_count == 0


def test_update_missing_collection_returns_none(mgr):
    assert mgr.update_collection("nope", {"title": "x"}) is None


# --------------------------------------------------------------------------- #
# Routes
# --------------------------------------------------------------------------- #
@pytest.fixture
def client(tmp_path, monkeypatch):
    import app.main as m
    from app.post_manager import PostManager
    from app.tag_manager import TagManager

    posts = tmp_path / "posts"
    pm = PostManager(posts, tmp_path / ".kb" / "search.db")
    bm = BookManager(tmp_path / "books")
    monkeypatch.setattr(m, "pm", pm)
    monkeypatch.setattr(m, "tm", TagManager(posts))
    monkeypatch.setattr(m, "books", bm)
    with TestClient(m.app) as c:
        c.books = bm
        yield c
    pm.search.close()


def test_create_form_has_cover_and_tags_fields(client):
    html = client.get("/books/new").text
    assert 'data-cover-file' in html
    assert 'name="cover"' in html
    assert 'name="tags"' in html


def test_create_collection_with_cover_via_form(client):
    r = client.post("/books/new", data={
        "title": "Harry Potter", "author": "JKR",
        "cover": "/img/hp.png", "tags": "fantasy, magic",
    }, follow_redirects=False)
    assert r.status_code == 303
    c = client.books.read_collection("harry-potter")
    assert c.cover == "/img/hp.png"
    assert c.tags == ["fantasy", "magic"]

    # cover + tags + date render on index and detail
    idx = client.get("/books").text
    assert 'src="/img/hp.png"' in idx
    assert "#fantasy" in idx
    detail = client.get("/books/harry-potter").text
    assert 'src="/img/hp.png"' in detail
    assert "#magic" in detail
    assert c.created in detail


def test_edit_collection_flow(client):
    client.post("/books/new", data={"title": "Dune"}, follow_redirects=False)
    # edit form reachable + not shadowed by chapter route
    assert client.get("/books/dune/edit").status_code == 200

    r = client.post("/books/dune/edit", data={
        "title": "Dune", "author": "Herbert",
        "cover": "/img/dune.png", "tags": "scifi",
    }, follow_redirects=False)
    assert r.status_code == 303
    c = client.books.read_collection("dune")
    assert c.cover == "/img/dune.png"
    assert c.author == "Herbert"
    assert c.tags == ["scifi"]


def test_placeholder_when_no_cover(client):
    client.post("/books/new", data={"title": "No Cover"}, follow_redirects=False)
    idx = client.get("/books").text
    assert "book-cover--placeholder" in idx


def test_app_js_has_cover_upload():
    js = (Path("static") / "app.js").read_text(encoding="utf-8")
    assert "initCoverUpload" in js
    assert "data-cover-file" in js
