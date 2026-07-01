"""Tests for playlist reorder (up/down) and the Play-all player markup."""

import io

import pytest
from fastapi.testclient import TestClient

from app.music import MusicManager

MP3 = b"ID3\x03\x00\x00\x00\x00\x00\x21fake\xff\xfb\x90\x00"


# --------------------------------------------------------------------------- #
# Manager: move_track
# --------------------------------------------------------------------------- #
@pytest.fixture
def mgr(tmp_path):
    return MusicManager(tmp_path / "music")


def _setup(mgr):
    a = mgr.import_track("a.mp3", MP3)
    b = mgr.import_track("b.mp3", MP3)
    c = mgr.import_track("c.mp3", MP3)
    pl = mgr.create_playlist({"title": "P"})
    for s in (a, b, c):
        mgr.add_to_playlist(pl, s)
    return pl, a, b, c


def test_move_down_and_up(mgr):
    pl, a, b, c = _setup(mgr)
    assert mgr.move_track(pl, a, "down") is True
    assert mgr.read_playlist(pl, resolve=False).track_slugs == [b, a, c]
    assert mgr.move_track(pl, a, "up") is True
    assert mgr.read_playlist(pl, resolve=False).track_slugs == [a, b, c]


def test_move_at_edge_is_noop(mgr):
    pl, a, b, c = _setup(mgr)
    assert mgr.move_track(pl, a, "up") is True          # already first
    assert mgr.read_playlist(pl, resolve=False).track_slugs == [a, b, c]
    assert mgr.move_track(pl, c, "down") is True         # already last
    assert mgr.read_playlist(pl, resolve=False).track_slugs == [a, b, c]


def test_move_unknown(mgr):
    pl, a, b, c = _setup(mgr)
    assert mgr.move_track(pl, "ghost", "up") is False
    assert mgr.move_track("noplaylist", a, "up") is False


# --------------------------------------------------------------------------- #
# Routes / templates
# --------------------------------------------------------------------------- #
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


def _seed(client):
    for n in ("a.mp3", "b.mp3"):
        client.post("/music/import", files={"file": (n, io.BytesIO(MP3), "audio/mpeg")},
                    follow_redirects=False)
    client.post("/music/playlists/new", data={"title": "Mix"}, follow_redirects=False)
    client.post("/music/playlists/mix/add", data={"track": "a"}, follow_redirects=False)
    client.post("/music/playlists/mix/add", data={"track": "b"}, follow_redirects=False)


def test_move_route_reorders(client):
    _seed(client)
    r = client.post("/music/playlists/mix/move", data={"track": "a", "direction": "down"},
                    follow_redirects=False)
    assert r.status_code == 303
    assert client.music.read_playlist("mix", resolve=False).track_slugs == ["b", "a"]


def test_move_bad_direction_404(client):
    _seed(client)
    assert client.post("/music/playlists/mix/move",
                       data={"track": "a", "direction": "sideways"}).status_code == 404


def test_detail_has_play_all_and_reorder_controls(client):
    _seed(client)
    html = client.get("/music/playlists/mix").text
    assert 'id="play-all"' in html               # play-all bar
    assert 'id="pa-data"' in html                 # track data for JS
    assert "Play all" in html
    assert 'value="up"' in html and 'value="down"' in html  # reorder buttons
    assert "initPlaylistPlayer()" in html


def test_app_js_has_player():
    from pathlib import Path
    js = (Path("static") / "app.js").read_text(encoding="utf-8")
    assert "initPlaylistPlayer" in js
    assert '"ended"' in js                        # auto-advance hook
