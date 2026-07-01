"""Tests for the back-to-top floating button."""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client(tmp_path, monkeypatch):
    import app.main as m
    from app.post_manager import PostManager
    from app.tag_manager import TagManager

    posts = tmp_path / "posts"
    pm = PostManager(posts, tmp_path / ".kb" / "search.db")
    monkeypatch.setattr(m, "pm", pm)
    monkeypatch.setattr(m, "tm", TagManager(posts))
    with TestClient(m.app) as c:
        yield c
    pm.search.close()


def test_button_renders_on_page(client):
    html = client.get("/").text
    assert 'id="to-top"' in html
    assert 'aria-label="Back to top"' in html


def test_app_js_has_scroll_logic():
    js = (Path("static") / "app.js").read_text(encoding="utf-8")
    assert "#to-top" in js
    assert "scrollTo" in js
    assert "behavior" in js  # smooth scroll


def test_css_has_to_top_styles():
    css = (Path("static") / "style.css").read_text(encoding="utf-8")
    assert ".to-top" in css
    assert ".to-top.visible" in css
    assert "position: fixed" in css
