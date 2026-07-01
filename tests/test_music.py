"""Tests for the Music feature (.mp3 import + markdown metadata) and Homepage."""

import io

import pytest
from fastapi.testclient import TestClient

from app.music import MusicManager

MP3 = b"ID3\x03\x00\x00\x00\x00\x00\x21fake-mp3-bytes-for-testing\xff\xfb\x90\x00"


# --------------------------------------------------------------------------- #
# MusicManager
# --------------------------------------------------------------------------- #
@pytest.fixture
def mgr(tmp_path):
    return MusicManager(tmp_path / "music")


def test_import_creates_mp3_and_md(mgr, tmp_path):
    slug = mgr.import_track("Bohemian Rhapsody.mp3", MP3)
    assert slug == "bohemian-rhapsody"
    assert (tmp_path / "music" / "bohemian-rhapsody.mp3").read_bytes() == MP3
    assert (tmp_path / "music" / "bohemian-rhapsody.md").exists()
    t = mgr.read(slug)
    assert t.title == "Bohemian Rhapsody"          # default title from filename
    assert t.audio_url == "/audio/bohemian-rhapsody.mp3"
    assert t.author == "" and t.year == ""


def test_update_metadata(mgr):
    slug = mgr.import_track("song.mp3", MP3)
    mgr.update(slug, {"title": "Song", "author": "Queen", "year": "1975",
                      "type": "Rock", "album": "A Night at the Opera",
                      "notes": "Iconic."})
    t = mgr.read(slug)
    assert t.author == "Queen" and t.year == "1975"
    assert t.type == "Rock" and t.album == "A Night at the Opera"
    assert t.notes == "Iconic."


def test_import_unique_slug(mgr):
    a = mgr.import_track("dup.mp3", MP3)
    b = mgr.import_track("dup.mp3", MP3)
    assert a == "dup" and b == "dup-2"


def test_delete_removes_both_files(mgr, tmp_path):
    slug = mgr.import_track("x.mp3", MP3)
    assert mgr.delete(slug) is True
    assert not (tmp_path / "music" / "x.mp3").exists()
    assert not (tmp_path / "music" / "x.md").exists()
    assert mgr.delete(slug) is False


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
    mm = MusicManager(tmp_path / "music")
    monkeypatch.setattr(m, "pm", pm)
    monkeypatch.setattr(m, "tm", TagManager(posts))
    monkeypatch.setattr(m, "music", mm)
    with TestClient(m.app) as c:
        c.music = mm
        yield c
    pm.search.close()


def test_music_button_in_topbar(client):
    assert 'href="/music"' in client.get("/").text


def test_music_index_empty(client):
    assert "No music yet" in client.get("/music").text


def test_import_flow_redirects_to_edit_and_persists(client):
    r = client.post("/music/import",
                    files={"file": ("My Song.mp3", io.BytesIO(MP3), "audio/mpeg")},
                    follow_redirects=False)
    assert r.status_code == 303
    assert r.headers["location"] == "/music/my-song/edit"
    assert client.music.read("my-song") is not None

    # edit form renders metadata fields + audio player
    form = client.get("/music/my-song/edit").text
    assert 'name="author"' in form and 'name="year"' in form and 'name="type"' in form
    assert "/audio/my-song.mp3" in form


def test_import_rejects_non_mp3(client):
    r = client.post("/music/import",
                    files={"file": ("note.txt", io.BytesIO(b"hi"), "text/plain")})
    assert r.status_code == 400


def test_edit_updates_and_index_lists(client):
    client.post("/music/import",
                files={"file": ("track.mp3", io.BytesIO(MP3), "audio/mpeg")},
                follow_redirects=False)
    r = client.post("/music/track/edit",
                    data={"title": "Track", "author": "Artist", "year": "2020",
                          "type": "Pop", "album": "Album", "notes": "n"},
                    follow_redirects=False)
    assert r.status_code == 303
    idx = client.get("/music").text
    assert "Track" in idx and "Artist" in idx and "Pop" in idx
    assert "<audio" in idx  # player rendered


def test_delete_route(client):
    client.post("/music/import",
                files={"file": ("gone.mp3", io.BytesIO(MP3), "audio/mpeg")},
                follow_redirects=False)
    r = client.post("/music/gone/delete", follow_redirects=False)
    assert r.status_code == 303
    assert client.music.read("gone") is None


# --------------------------------------------------------------------------- #
# Homepage
# --------------------------------------------------------------------------- #
def test_homepage_shows_feature_boxes(client):
    html = client.get("/").text
    assert "home-grid" in html
    for href in ['href="/posts"', 'href="/series"', 'href="/books"',
                 'href="/toeic"', 'href="/music"']:
        assert href in html


def test_posts_feed_moved_to_posts(client):
    # the posts feed lives at /posts now; / is the homepage
    assert "home-grid" in client.get("/").text
    assert client.get("/posts").status_code == 200
