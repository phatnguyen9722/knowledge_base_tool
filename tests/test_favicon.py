"""Favicon should be declared and served (no more /favicon.ico 404)."""

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client(tmp_path, monkeypatch):
    import app.main as m
    from app.post_manager import PostManager
    from app.tag_manager import TagManager

    pm = PostManager(tmp_path / "posts", tmp_path / ".kb" / "search.db")
    monkeypatch.setattr(m, "pm", pm)
    monkeypatch.setattr(m, "tm", TagManager(tmp_path / "posts"))
    with TestClient(m.app) as c:
        yield c
    pm.search.close()


def test_favicon_route_serves_png(client):
    r = client.get("/favicon.ico")
    assert r.status_code == 200
    assert r.headers["content-type"] == "image/png"


def test_pages_declare_favicon_link(client):
    assert 'rel="icon"' in client.get("/").text
