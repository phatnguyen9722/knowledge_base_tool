"""Tests for per-note themes, the click-to-open detail view, and fixed boxes."""

import pytest
from fastapi.testclient import TestClient

from app.notes import NOTE_THEMES, NoteManager


# --------------------------------------------------------------------------- #
# Manager: theme field
# --------------------------------------------------------------------------- #
@pytest.fixture
def mgr(tmp_path):
    return NoteManager(tmp_path / "notes")


def test_theme_defaults_to_plain(mgr):
    slug = mgr.create({"title": "T"})
    assert mgr.read(slug).theme == "plain"


def test_theme_persists_and_validates(mgr):
    slug = mgr.create({"title": "T", "theme": "dots"})
    assert mgr.read(slug).theme == "dots"
    # invalid theme falls back to plain
    mgr.update(slug, {"theme": "bogus"})
    assert mgr.read(slug).theme == "plain"
    # all advertised themes are accepted
    for th in NOTE_THEMES:
        mgr.update(slug, {"theme": th})
        assert mgr.read(slug).theme == th


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


def test_editor_has_theme_select(client):
    html = client.get("/notes/new").text
    assert 'name="theme"' in html
    for th in NOTE_THEMES:
        assert f'value="{th}"' in html


def test_create_with_theme_applies_class_and_open_link(client):
    client.post("/notes/new",
                data={"title": "Lined Note", "theme": "lines", "content": "x"},
                follow_redirects=False)
    html = client.get("/notes").text
    assert "note-theme-lines" in html              # theme class on the box
    assert 'href="/notes/lined-note"' in html      # click-to-open link
    assert 'class="note-open"' in html


def test_note_detail_renders_full_content(client):
    client.post("/notes/new",
                data={"title": "Full", "theme": "dots",
                      "content": "# Heading\n\nlong **body** text"},
                follow_redirects=False)
    html = client.get("/notes/full").text
    assert "note-detail" in html
    assert "note-theme-dots" in html
    assert "<strong>body</strong>" in html         # full markdown rendered
    assert '<h1 id="heading">Heading</h1>' in html


def test_detail_404(client):
    assert client.get("/notes/missing").status_code == 404


def test_new_not_shadowed_by_detail(client):
    # /notes/new must render the form, not be treated as a slug
    assert client.get("/notes/new").status_code == 200
    assert "<form" in client.get("/notes/new").text


def test_fixed_box_css_present():
    from pathlib import Path
    css = (Path("static") / "style.css").read_text(encoding="utf-8")
    assert "height: 240px" in css                  # fixed-size box
    assert ".note-open" in css                      # stretched click target
    for th in ["lines", "dots", "grid", "sticky"]:
        assert f".note-theme-{th}" in css
