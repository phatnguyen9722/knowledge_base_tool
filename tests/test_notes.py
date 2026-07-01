"""Tests for the Notes feature (Title/date/content + pin-to-favorite)."""

import pytest
from fastapi.testclient import TestClient

from app.notes import NoteManager


# --------------------------------------------------------------------------- #
# NoteManager
# --------------------------------------------------------------------------- #
@pytest.fixture
def mgr(tmp_path):
    return NoteManager(tmp_path / "notes")


def test_create_read_defaults_date(mgr):
    slug = mgr.create({"title": "Shopping", "content": "milk, eggs"})
    n = mgr.read(slug)
    assert n.title == "Shopping"
    assert n.content == "milk, eggs"
    assert n.date  # defaulted to today
    assert n.pinned is False


def test_files_stored_in_notes_dir(tmp_path):
    mgr = NoteManager(tmp_path / "notes")
    slug = mgr.create({"title": "Idea"})
    assert (tmp_path / "notes" / f"{slug}.md").exists()


def test_toggle_pin(mgr):
    slug = mgr.create({"title": "Fav"})
    assert mgr.toggle_pin(slug) is True
    assert mgr.read(slug).pinned is True
    assert mgr.toggle_pin(slug) is False
    assert mgr.read(slug).pinned is False


def test_list_pinned_first_then_date(mgr):
    mgr.create({"title": "Old", "date": "2024-01-01"})
    mgr.create({"title": "New", "date": "2026-01-01"})
    p = mgr.create({"title": "Pinned Old", "date": "2023-01-01"})
    mgr.toggle_pin(p)

    titles = [n.title for n in mgr.list()]
    assert titles[0] == "Pinned Old"          # pinned floats up
    assert titles[1:] == ["New", "Old"]       # then newest date first


def test_update_and_delete(mgr):
    slug = mgr.create({"title": "Draft", "content": "x"})
    mgr.update(slug, {"title": "Final", "content": "y"})
    assert mgr.read(slug).title == "Final"
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
    nm = NoteManager(tmp_path / "notes")
    monkeypatch.setattr(m, "pm", pm)
    monkeypatch.setattr(m, "tm", TagManager(tmp_path / "posts"))
    monkeypatch.setattr(m, "notes", nm)
    with TestClient(m.app) as c:
        c.notes = nm
        yield c
    pm.search.close()


def test_notes_button_and_homepage_box(client):
    home = client.get("/").text
    assert 'href="/notes"' in home          # topbar + homepage box


def test_notes_index_empty(client):
    assert "No notes yet" in client.get("/notes").text


def test_create_note_via_form_shows_as_box(client):
    r = client.post("/notes/new",
                    data={"title": "Reminder", "date": "2026-06-29",
                          "content": "Call **Alice**"},
                    follow_redirects=False)
    assert r.status_code == 303
    html = client.get("/notes").text
    assert "notes-grid" in html
    assert "Reminder" in html
    assert "<strong>Alice</strong>" in html   # content rendered as markdown
    assert "2026-06-29" in html


def test_pin_toggle_via_route_floats_to_top(client):
    client.post("/notes/new", data={"title": "A", "date": "2026-01-01"}, follow_redirects=False)
    client.post("/notes/new", data={"title": "B", "date": "2026-02-01"}, follow_redirects=False)
    # pin the older one
    client.post("/notes/a/pin", follow_redirects=False)
    listed = [n.title for n in client.notes.list()]
    assert listed[0] == "A"


def test_edit_and_delete_routes(client):
    client.post("/notes/new", data={"title": "Temp", "content": "x"}, follow_redirects=False)
    assert client.get("/notes/temp/edit").status_code == 200
    client.post("/notes/temp/edit", data={"title": "Temp2", "content": "y"}, follow_redirects=False)
    assert client.notes.read("temp").title == "Temp2"
    r = client.post("/notes/temp/delete", follow_redirects=False)
    assert r.status_code == 303
    assert client.notes.read("temp") is None


def test_missing_note_404(client):
    assert client.get("/notes/nope/edit").status_code == 404
    assert client.post("/notes/nope/pin").status_code == 404
