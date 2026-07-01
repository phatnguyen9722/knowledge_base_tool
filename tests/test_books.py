"""Tests for the Books feature (collections → chapters) + search-bar width."""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.books import BookManager


# --------------------------------------------------------------------------- #
# BookManager
# --------------------------------------------------------------------------- #
@pytest.fixture
def mgr(tmp_path):
    return BookManager(tmp_path / "books")


def test_create_collection_then_read(mgr):
    slug = mgr.create_collection({"title": "Harry Potter", "author": "J.K. Rowling",
                                  "description": "A wizard."})
    assert slug == "harry-potter"
    coll = mgr.read_collection(slug)
    assert coll.title == "Harry Potter"
    assert coll.author == "J.K. Rowling"
    assert coll.chapter_count == 0


def test_chapter_requires_existing_collection(mgr):
    # no collection yet → create_chapter returns None
    assert mgr.create_chapter("nope", {"title": "Ch1", "content": "x"}) is None


def test_create_chapters_ordered(mgr):
    mgr.create_collection({"title": "Harry Potter"})
    mgr.create_chapter("harry-potter", {"title": "The Vanishing Glass", "order": 2,
                                        "content": "# Glass\n\ntext"})
    mgr.create_chapter("harry-potter", {"title": "The Boy Who Lived", "order": 1,
                                        "content": "intro"})
    coll = mgr.read_collection("harry-potter")
    assert [c.title for c in coll.chapters] == ["The Boy Who Lived", "The Vanishing Glass"]
    ch = mgr.read_chapter("harry-potter", "the-boy-who-lived")
    assert ch.order == 1 and ch.content == "intro"


def test_collection_files_live_under_books_dir(tmp_path):
    mgr = BookManager(tmp_path / "books")
    mgr.create_collection({"title": "Dune"})
    mgr.create_chapter("dune", {"title": "Arrakis", "content": "sand"})
    assert (tmp_path / "books" / "dune" / "_collection.md").exists()
    assert (tmp_path / "books" / "dune" / "arrakis.md").exists()


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


def test_books_button_in_topbar(client):
    assert 'href="/books"' in client.get("/").text


def test_books_index_empty_then_new_collection_flow(client):
    assert "No collections yet" in client.get("/books").text

    r = client.post("/books/new", data={"title": "Harry Potter", "author": "JKR",
                                         "description": "wizard"},
                    follow_redirects=False)
    assert r.status_code == 303
    assert r.headers["location"] == "/books/harry-potter"
    assert "Harry Potter" in client.get("/books").text


def test_new_collection_route_not_shadowed(client):
    assert client.get("/books/new").status_code == 200


def test_create_chapter_flow_and_read(client):
    client.post("/books/new", data={"title": "Harry Potter"}, follow_redirects=False)

    # new chapter form available
    assert client.get("/books/harry-potter/new").status_code == 200

    r = client.post("/books/harry-potter/new",
                    data={"title": "The Boy Who Lived", "order": "1",
                          "content": "# Start\n\nMr and Mrs Dursley..."},
                    follow_redirects=False)
    assert r.status_code == 303
    assert r.headers["location"] == "/books/harry-potter/the-boy-who-lived"

    # collection detail lists the chapter
    detail = client.get("/books/harry-potter").text
    assert "The Boy Who Lived" in detail

    # chapter renders markdown + chapter position
    ch = client.get("/books/harry-potter/the-boy-who-lived").text
    assert "Mr and Mrs Dursley" in ch
    assert "Chapter 1 of 1" in ch


def test_chapter_prev_next_nav(client):
    client.post("/books/new", data={"title": "Series"}, follow_redirects=False)
    for i, t in enumerate(["One", "Two", "Three"], start=1):
        client.post("/books/series/new", data={"title": t, "order": str(i),
                                               "content": t}, follow_redirects=False)
    mid = client.get("/books/series/two").text
    assert "Chapter 2 of 3" in mid
    assert "/books/series/one" in mid   # prev
    assert "/books/series/three" in mid  # next


def test_missing_collection_404(client):
    assert client.get("/books/nope").status_code == 404
    assert client.get("/books/nope/new").status_code == 404


# --------------------------------------------------------------------------- #
# Search bar width
# --------------------------------------------------------------------------- #
def test_search_bar_width_capped():
    # Search bar is constrained to a fixed share of the header (not flex:1).
    css = (Path("static") / "style.css").read_text(encoding="utf-8")
    assert ".search-wrap { flex: 0 0" in css
    assert "%;" in css.split(".search-wrap { flex: 0 0", 1)[1].split("\n", 1)[0]
