"""Tests for icon library: list + delete endpoints."""

import io
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

PNG = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
    b"\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc\x00\x01"
    b"\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82"
)
PNG2 = PNG[:20] + b"\x00" * 20 + PNG[40:]   # slightly different bytes


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


def _upload(client, data=PNG, name="icon.png"):
    return client.post("/api/upload-icon",
                       files={"file": (name, io.BytesIO(data), "image/png")}).json()


def test_list_icons_empty(client):
    r = client.get("/api/icons")
    assert r.status_code == 200
    assert r.json() == []


def test_list_icons_after_upload(client):
    up1 = _upload(client, PNG, "a.png")
    up2 = _upload(client, PNG2, "b.png")
    icons = client.get("/api/icons").json()
    assert len(icons) == 2
    urls = {i["url"] for i in icons}
    assert up1["url"] in urls
    assert up2["url"] in urls
    # each item has url + filename
    assert all("filename" in i and "url" in i for i in icons)


def test_delete_icon(client):
    up = _upload(client)
    filename = up["filename"]
    # icon exists on disk
    assert (client.img_dir / "icons" / filename).exists()
    r = client.delete(f"/api/icons/{filename}")
    assert r.status_code == 200
    assert r.json() == {"ok": True}
    # removed from disk
    assert not (client.img_dir / "icons" / filename).exists()
    # no longer in list
    assert not any(i["filename"] == filename for i in client.get("/api/icons").json())


def test_delete_missing_icon_404(client):
    assert client.delete("/api/icons/ghost.png").status_code == 404


def test_delete_rejects_dotdot_in_filename(client):
    # Filenames containing ".." are rejected with 400.
    assert client.delete("/api/icons/..bad..file.png").status_code == 400
    # Paths with slashes won't route to this endpoint at all (FastAPI 404s them).
    assert client.delete("/api/icons/sub%2Fpath.png").status_code in (400, 404, 422)


def test_settings_modal_has_library_section(client):
    html = client.get("/").text
    assert 'id="icon-library"' in html
    assert "Icon Library" in html


def test_app_js_has_library_functions():
    js = Path("static/app.js").read_text(encoding="utf-8")
    assert "loadIconLibrary" in js
    assert "_renderIconPage" in js
    assert "ICONS_PER_PAGE" in js
    assert "_iconLibPage" in js
    assert "/api/icons" in js
    assert "icon-lib-del" in js
    assert "icon-lib-select" in js
    assert "icon-lib-prev" in js
    assert "icon-lib-next" in js


def test_icons_per_page_constant():
    js = Path("static/app.js").read_text(encoding="utf-8")
    import re
    m = re.search(r"var ICONS_PER_PAGE\s*=\s*(\d+)", js)
    assert m, "ICONS_PER_PAGE not found"
    assert int(m.group(1)) >= 10   # currently 12; at least 10 per page
