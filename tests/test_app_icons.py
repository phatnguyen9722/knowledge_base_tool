"""Tests for custom app icons (upload to img/icons/, Settings picker, data-app spans)."""

import io
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

PNG = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
    b"\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc\x00\x01"
    b"\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82"
)


@pytest.fixture
def client(tmp_path, monkeypatch):
    import app.main as m
    from app.post_manager import PostManager
    from app.tag_manager import TagManager

    pm = PostManager(tmp_path / "posts", tmp_path / ".kb" / "search.db")
    monkeypatch.setattr(m, "pm", pm)
    monkeypatch.setattr(m, "tm", TagManager(tmp_path / "posts"))
    monkeypatch.setattr(m, "IMG_DIR", tmp_path / "img")
    with TestClient(m.app) as c:
        c.img_dir = tmp_path / "img"
        yield c
    pm.search.close()


def test_upload_icon_stores_in_icons_subdir(client, tmp_path, monkeypatch):
    import app.main as m
    monkeypatch.setattr(m, "IMG_DIR", tmp_path / "img")
    r = client.post("/api/upload-icon",
                    files={"file": ("my-icon.png", io.BytesIO(PNG), "image/png")})
    assert r.status_code == 200
    data = r.json()
    assert data["url"].startswith("/img/icons/")
    assert data["url"].endswith(".png")
    assert (tmp_path / "img" / "icons" / data["filename"]).exists()


def test_upload_icon_dedupes_same_content(client, tmp_path, monkeypatch):
    import app.main as m
    monkeypatch.setattr(m, "IMG_DIR", tmp_path / "img")
    r1 = client.post("/api/upload-icon",
                     files={"file": ("a.png", io.BytesIO(PNG), "image/png")})
    r2 = client.post("/api/upload-icon",
                     files={"file": ("b.png", io.BytesIO(PNG), "image/png")})
    assert r1.json()["filename"] == r2.json()["filename"]
    assert len(list((tmp_path / "img" / "icons").iterdir())) == 1


def test_upload_icon_rejects_non_image(client):
    r = client.post("/api/upload-icon",
                    files={"file": ("text.txt", io.BytesIO(b"hello"), "text/plain")})
    assert r.status_code == 400


def test_topbar_has_data_app_spans(client):
    html = client.get("/").text
    for app in ("api-docs", "notes", "books", "music", "toeic", "series"):
        assert f'data-app="{app}"' in html


def test_home_cards_have_data_app(client):
    html = client.get("/").text
    # home cards carry data-app on the icon span
    for app in ("posts", "notes", "books", "music", "toeic", "series", "api-docs"):
        assert f'data-app="{app}"' in html


def test_settings_modal_has_icon_picker(client):
    html = client.get("/").text
    assert 'id="icon-picker-list"' in html
    assert "App Icons" in html


def test_app_js_has_icon_functions():
    js = Path("static/app.js").read_text(encoding="utf-8")
    assert "APP_ICONS_DEFAULT" in js
    assert "applyAppIcons" in js
    assert "buildIconPicker" in js
    assert "setAppIcon" in js
    assert "resetAppIcon" in js
    assert "/api/upload-icon" in js


def test_css_has_icon_styles():
    css = Path("static/style.css").read_text(encoding="utf-8")
    assert ".app-icon-img" in css
    assert ".icon-picker-row" in css
    assert ".icon-picker-current" in css
