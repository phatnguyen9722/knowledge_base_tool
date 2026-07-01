"""Tests for song cover images and playlists."""

import io

import pytest
from fastapi.testclient import TestClient

from app.music import MusicManager

MP3 = b"ID3\x03\x00\x00\x00\x00\x00\x21fake\xff\xfb\x90\x00"


# --------------------------------------------------------------------------- #
# Cover per song
# --------------------------------------------------------------------------- #
@pytest.fixture
def mgr(tmp_path):
    return MusicManager(tmp_path / "music")


def test_track_cover_defaults_empty_then_set(mgr):
    slug = mgr.import_track("song.mp3", MP3)
    assert mgr.read(slug).cover == ""
    mgr.update(slug, {"title": "Song", "cover": "/img/cover.png"})
    assert mgr.read(slug).cover == "/img/cover.png"


# --------------------------------------------------------------------------- #
# Playlist manager
# --------------------------------------------------------------------------- #
def test_create_playlist_and_add_remove(mgr):
    a = mgr.import_track("a.mp3", MP3)
    b = mgr.import_track("b.mp3", MP3)
    pl = mgr.create_playlist({"title": "Chill", "description": "easy"})

    assert mgr.read_playlist(pl).count == 0
    assert mgr.add_to_playlist(pl, a) is True
    assert mgr.add_to_playlist(pl, b) is True
    assert mgr.add_to_playlist(pl, a) is True          # idempotent (no dup)
    got = mgr.read_playlist(pl)
    assert got.track_slugs == [a, b]
    assert [t.slug for t in got.tracks] == [a, b]      # resolved, in order

    assert mgr.remove_from_playlist(pl, a) is True
    assert mgr.read_playlist(pl).track_slugs == [b]


def test_add_missing_track_or_playlist(mgr):
    pl = mgr.create_playlist({"title": "P"})
    assert mgr.add_to_playlist(pl, "ghost") is False   # track doesn't exist
    assert mgr.add_to_playlist("noplaylist", "x") is False


def test_playlist_files_under_music_playlists(tmp_path):
    mgr = MusicManager(tmp_path / "music")
    slug = mgr.create_playlist({"title": "My List"})
    assert (tmp_path / "music" / "playlists" / f"{slug}.md").exists()


def test_deleted_track_drops_from_playlist_view(mgr):
    a = mgr.import_track("a.mp3", MP3)
    pl = mgr.create_playlist({"title": "P"})
    mgr.add_to_playlist(pl, a)
    mgr.delete(a)
    got = mgr.read_playlist(pl)
    assert got.track_slugs == [a]        # slug kept on disk
    assert got.tracks == []              # but not resolved (track gone)


# --------------------------------------------------------------------------- #
# Routes
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


def _import(client, name):
    client.post("/music/import",
                files={"file": (name, io.BytesIO(MP3), "audio/mpeg")},
                follow_redirects=False)


def test_music_edit_has_cover_field(client):
    _import(client, "s.mp3")
    form = client.get("/music/s/edit").text
    assert 'name="cover"' in form and "data-cover-file" in form


def test_cover_shows_on_index(client):
    _import(client, "s.mp3")
    client.post("/music/s/edit", data={"title": "S", "cover": "/img/c.png"},
                follow_redirects=False)
    assert 'src="/img/c.png"' in client.get("/music").text


def test_playlists_link_on_music_page(client):
    assert 'href="/music/playlists"' in client.get("/music").text


def test_playlist_routes_not_shadowed(client):
    assert client.get("/music/playlists").status_code == 200
    assert client.get("/music/playlists/new").status_code == 200


def test_playlist_create_add_remove_via_routes(client):
    _import(client, "Song A.mp3")
    _import(client, "Song B.mp3")
    r = client.post("/music/playlists/new",
                    data={"title": "Roadtrip", "description": "go"},
                    follow_redirects=False)
    assert r.status_code == 303
    assert r.headers["location"] == "/music/playlists/roadtrip"

    # add-song select offers available tracks
    detail = client.get("/music/playlists/roadtrip").text
    assert "Add a song" in detail and "song-a" in detail

    client.post("/music/playlists/roadtrip/add", data={"track": "song-a"},
                follow_redirects=False)
    detail = client.get("/music/playlists/roadtrip").text
    assert "Song A" in detail
    assert "1 track" in detail

    client.post("/music/playlists/roadtrip/remove", data={"track": "song-a"},
                follow_redirects=False)
    assert client.music.read_playlist("roadtrip").count == 0


def test_playlist_delete(client):
    client.post("/music/playlists/new", data={"title": "Temp"}, follow_redirects=False)
    r = client.post("/music/playlists/temp/delete", follow_redirects=False)
    assert r.status_code == 303
    assert client.music.read_playlist("temp") is None
