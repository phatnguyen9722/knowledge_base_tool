"""Tests for creating TOEIC sets via the UI, and the relocated New buttons."""

import pytest
from fastapi.testclient import TestClient

from app.toeic import ToeicManager


@pytest.fixture
def client(tmp_path, monkeypatch):
    import app.main as m
    from app.post_manager import PostManager
    from app.tag_manager import TagManager

    posts = tmp_path / "posts"
    pm = PostManager(posts, tmp_path / ".kb" / "search.db")
    tmgr = ToeicManager(tmp_path / "toeic")
    monkeypatch.setattr(m, "pm", pm)
    monkeypatch.setattr(m, "tm", TagManager(posts))
    monkeypatch.setattr(m, "toeic", tmgr)
    with TestClient(m.app) as c:
        c.toeic = tmgr
        yield c
    pm.search.close()


# --------------------------------------------------------------------------- #
# Manager.create
# --------------------------------------------------------------------------- #
def test_manager_create_writes_file_and_parses_back(tmp_path):
    mgr = ToeicManager(tmp_path / "toeic")
    slug = mgr.create({
        "title": "Part 6 — Set X", "part": 6, "tags": ["GRAMMAR"],
        "summary": "demo",
        "content": "::: question\nQ?\n- A. one\n- B. two\nanswer: B\nnote: because.\n:::\n",
    })
    assert slug == "part-6-set-x"
    assert (tmp_path / "toeic" / "part-6-set-x.md").exists()
    s = mgr.read(slug)
    assert s.part == 6 and s.tags == ["grammar"]
    assert len(s.questions) == 1 and s.questions[0].answer == "B"


def test_manager_create_unique_slug(tmp_path):
    mgr = ToeicManager(tmp_path / "toeic")
    a = mgr.create({"title": "Same", "part": 5, "content": ""})
    b = mgr.create({"title": "Same", "part": 5, "content": ""})
    assert a == "same" and b == "same-2"


# --------------------------------------------------------------------------- #
# Routes
# --------------------------------------------------------------------------- #
def test_toeic_new_form_renders(client):
    html = client.get("/toeic/new").text
    assert "<form" in html and 'action="/toeic/new"' in html
    assert 'name="part"' in html
    # skeleton prefilled
    assert "::: question" in html


def test_toeic_new_route_not_shadowed_by_detail(client):
    # /toeic/new must render the form, not 404 as a missing slug
    assert client.get("/toeic/new").status_code == 200


def test_toeic_create_via_form_redirects_and_persists(client):
    r = client.post("/toeic/new", data={
        "title": "Part 5 — Created",
        "part": "5",
        "tags": "grammar, verbs",
        "summary": "made in test",
        "content": "::: question\nPick one.\n- A. x\n- B. y\nanswer: A\n:::\n",
    }, follow_redirects=False)
    assert r.status_code == 303
    assert r.headers["location"] == "/toeic/part-5-created"

    s = client.toeic.read("part-5-created")
    assert s is not None
    assert s.part == 5
    assert s.tags == ["grammar", "verbs"]
    assert s.questions[0].answer == "A"

    # and it now shows on the index + its detail renders radios
    assert "Part 5 — Created" in client.get("/toeic").text
    assert 'type="radio"' in client.get("/toeic/part-5-created").text


# --------------------------------------------------------------------------- #
# New buttons moved off the global topbar onto each page
# --------------------------------------------------------------------------- #
def test_global_new_button_removed_from_topbar(client):
    # The posts page still has its own New button, but it's in the feed-head,
    # not a always-present topbar button. Easiest invariant: the TOEIC index
    # has a New TOEIC button and NOT a "New post" one.
    toeic_html = client.get("/toeic").text
    assert 'href="/toeic/new"' in toeic_html
    assert "New TOEIC" in toeic_html


def test_posts_page_has_new_post_button(client):
    html = client.get("/posts").text
    assert 'href="/new"' in html
    assert "New post" in html


def test_toeic_page_has_no_new_post_button(client):
    # No link to the post editor on the TOEIC page (the "New post" text in the
    # keyboard-shortcut help modal is fine — we check for the actual link).
    html = client.get("/toeic").text
    assert 'href="/new"' not in html
