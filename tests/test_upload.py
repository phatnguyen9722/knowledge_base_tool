"""Tests for pasting/uploading images into the editor (/api/upload)."""

import io

import pytest
from fastapi.testclient import TestClient

# 1x1 transparent PNG
PNG_BYTES = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
    b"\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc\x00\x01"
    b"\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82"
)


@pytest.fixture
def client(tmp_path, monkeypatch):
    import app.main as m
    from app.post_manager import PostManager
    from app.tag_manager import TagManager

    posts = tmp_path / "posts"
    img = tmp_path / "img"
    pm = PostManager(posts, tmp_path / ".kb" / "search.db")
    monkeypatch.setattr(m, "pm", pm)
    monkeypatch.setattr(m, "tm", TagManager(posts))
    monkeypatch.setattr(m, "IMG_DIR", img)
    with TestClient(m.app) as c:
        c.img_dir = img
        yield c
    pm.search.close()


def test_upload_png_saves_and_returns_markdown(client):
    r = client.post(
        "/api/upload",
        files={"file": ("paste.png", io.BytesIO(PNG_BYTES), "image/png")},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["url"].startswith("/img/")
    assert body["url"].endswith(".png")
    assert body["markdown"] == f"![]({body['url']})"
    # file actually written into the img dir
    saved = client.img_dir / body["filename"]
    assert saved.exists()
    assert saved.read_bytes() == PNG_BYTES


def test_upload_is_content_addressed_and_dedupes(client):
    r1 = client.post("/api/upload",
                     files={"file": ("a.png", io.BytesIO(PNG_BYTES), "image/png")})
    r2 = client.post("/api/upload",
                     files={"file": ("b.png", io.BytesIO(PNG_BYTES), "image/png")})
    # identical bytes -> identical filename (deduped), regardless of upload name
    assert r1.json()["filename"] == r2.json()["filename"]
    assert len(list(client.img_dir.iterdir())) == 1


def test_upload_rejects_non_image(client):
    r = client.post(
        "/api/upload",
        files={"file": ("note.txt", io.BytesIO(b"hello"), "text/plain")},
    )
    assert r.status_code == 400


def test_upload_rejects_empty(client):
    r = client.post(
        "/api/upload",
        files={"file": ("empty.png", io.BytesIO(b""), "image/png")},
    )
    assert r.status_code == 400


def test_app_js_has_paste_upload_logic():
    from pathlib import Path

    js = (Path("static") / "app.js").read_text(encoding="utf-8")
    assert "paste" in js
    assert "/api/upload" in js
    assert "uploadImage" in js
