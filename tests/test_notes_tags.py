"""Tests for Notes tags, tag filtering, and name/content mini-search."""

import pytest
from fastapi.testclient import TestClient

from app.notes import NoteManager


# --------------------------------------------------------------------------- #
# Manager
# --------------------------------------------------------------------------- #
@pytest.fixture
def mgr(tmp_path):
    return NoteManager(tmp_path / "notes")


def test_tags_persist_normalized(mgr):
    slug = mgr.create({"title": "T", "tags": ["Work", " IDEAS "]})
    assert mgr.read(slug).tags == ["work", "ideas"]


def test_all_tags_counts(mgr):
    mgr.create({"title": "A", "tags": ["work", "idea"]})
    mgr.create({"title": "B", "tags": ["work"]})
    tags = mgr.all_tags()
    assert tags["work"] == 2 and tags["idea"] == 1


def test_list_filter_by_tags_and(mgr):
    mgr.create({"title": "Both", "tags": ["work", "urgent"]})
    mgr.create({"title": "WorkOnly", "tags": ["work"]})
    assert {n.title for n in mgr.list(tags=["work"])} == {"Both", "WorkOnly"}
    assert [n.title for n in mgr.list(tags=["work", "urgent"])] == ["Both"]


def test_list_filter_by_name_and_content(mgr):
    mgr.create({"title": "Grocery list", "content": "milk"})
    mgr.create({"title": "Meeting", "content": "discuss milk delivery"})
    mgr.create({"title": "Other", "content": "nothing"})
    # by name
    assert [n.title for n in mgr.list(q="grocery")] == ["Grocery list"]
    # by content
    assert {n.title for n in mgr.list(q="milk")} == {"Grocery list", "Meeting"}


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


def _mk(client, title, tags="", content=""):
    client.post("/notes/new",
                data={"title": title, "tags": tags, "content": content},
                follow_redirects=False)


def test_create_with_tags_renders_chips(client):
    _mk(client, "Tagged", tags="work, idea")
    html = client.get("/notes").text
    assert "#work" in html and "#idea" in html
    assert "tag-cloud" in html             # sidebar tag filter
    assert 'name="q"' in html              # mini search bar


def test_filter_by_tag(client):
    _mk(client, "Work note", tags="work")
    _mk(client, "Home note", tags="home")
    html = client.get("/notes", params={"tag": ["work"]}).text
    assert "Work note" in html
    assert "Home note" not in html


def test_filter_by_two_tags_and(client):
    _mk(client, "Both", tags="work, urgent")
    _mk(client, "One", tags="work")
    html = client.get("/notes", params={"tag": ["work", "urgent"]}).text
    assert "Both" in html and "One" not in html
    assert "all tags (AND)" in html


def test_mini_search_by_name(client):
    _mk(client, "Grocery list", content="milk")
    _mk(client, "Meeting", content="agenda")
    html = client.get("/notes", params={"q": "grocery"}).text
    assert "Grocery list" in html
    assert "Meeting" not in html


def test_search_keeps_active_tag_hidden_input(client):
    _mk(client, "X", tags="work")
    html = client.get("/notes", params={"tag": ["work"]}).text
    # the mini search form preserves the active tag filter
    assert '<input type="hidden" name="tag" value="work">' in html


def test_edit_form_has_tags_field(client):
    _mk(client, "Editable", tags="a")
    assert 'name="tags"' in client.get("/notes/editable/edit").text
