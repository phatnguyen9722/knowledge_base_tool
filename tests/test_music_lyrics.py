"""Tests for song lyrics (stored as the markdown body) + show/hide rendering."""

import io

import pytest
from fastapi.testclient import TestClient

from app.music import MusicManager

MP3 = b"ID3\x03\x00\x00\x00\x00\x00\x21fake\xff\xfb\x90\x00"
LYRICS = "Is this the real life?\nIs this just fantasy?\n\nCaught in a landslide..."


@pytest.fixture
def mgr(tmp_path):
    return MusicManager(tmp_path / "music")


def test_lyrics_persist_with_line_breaks(mgr):
    slug = mgr.import_track("bohemian.mp3", MP3)
    assert mgr.read(slug).lyrics == ""  # none on import
    mgr.update(slug, {"title": "Bohemian Rhapsody", "lyrics": LYRICS,
                      "notes": "a note"})
    t = mgr.read(slug)
    assert t.lyrics == LYRICS
    assert "\n" in t.lyrics            # line breaks preserved
    assert t.notes == "a note"         # notes separate from lyrics


@pytest.fixture
def client(tmp_path, monkeypatch):
    import app.main as m
    from app.post_manager import PostManager
    from app.tag_manager import TagManager

    pm = PostManager(tmp_path / "posts", tmp_path / ".kb" / "search.db")
    mm = MusicManager(tmp_path / "music")
    monkeypatch.setattr(m, "pm", pm)
    monkeypatch.setattr(m, "tm", TagManager(tmp_path / "posts"))
    monkeypatch.setattr(m, "music", mm)
    with TestClient(m.app) as c:
        c.music = mm
        yield c
    pm.search.close()


def test_edit_form_has_lyrics_field(client):
    client.post("/music/import",
                files={"file": ("s.mp3", io.BytesIO(MP3), "audio/mpeg")},
                follow_redirects=False)
    form = client.get("/music/s/edit").text
    assert 'name="lyrics"' in form
    assert ">Lyrics<" in form


def test_lyrics_show_hide_on_index(client):
    client.post("/music/import",
                files={"file": ("song.mp3", io.BytesIO(MP3), "audio/mpeg")},
                follow_redirects=False)
    client.post("/music/song/edit",
                data={"title": "Song", "lyrics": LYRICS}, follow_redirects=False)

    html = client.get("/music").text
    # native show/hide via <details>/<summary>
    assert "<details" in html
    assert "<summary>Lyrics</summary>" in html
    assert "Is this the real life?" in html


def test_no_lyrics_block_when_empty(client):
    client.post("/music/import",
                files={"file": ("nolyric.mp3", io.BytesIO(MP3), "audio/mpeg")},
                follow_redirects=False)
    html = client.get("/music").text
    assert "<summary>Lyrics</summary>" not in html
