"""Tests for the copy-to-clipboard code-block feature.

The clipboard interaction is browser-only; here we verify the render target
(a <pre><code> block on the detail page) and that the JS/CSS carry the
copy-button logic.
"""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

CODE_POST = "Intro text\n\n```python\nprint('hi')\n```\n\nmore\n"


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
        c.pm = pm
        yield c
    pm.search.close()


def test_detail_renders_code_block(client):
    client.pm.create({
        "title": "Snippet", "tags": [], "category": "G", "status": "published",
        "content": CODE_POST,
    })
    html = client.get("/posts/snippet").text
    assert "<pre>" in html          # copy buttons attach to <pre> elements
    assert "<code" in html
    assert "print" in html


def test_app_js_has_copy_logic():
    js = (Path("static") / "app.js").read_text(encoding="utf-8")
    assert "enhanceCodeBlocks" in js
    assert "copy-btn" in js
    assert "clipboard" in js
    assert "legacyCopy" in js        # fallback for non-clipboard contexts


def test_css_has_copy_styles():
    css = (Path("static") / "style.css").read_text(encoding="utf-8")
    assert ".code-block" in css
    assert ".copy-btn" in css
    assert ".copy-btn.copied" in css
