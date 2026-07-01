"""Tests for Table-of-Contents rendering (app/markdown.py + detail page)."""

import pytest
from fastapi.testclient import TestClient

from app.markdown import render_with_toc


# --------------------------------------------------------------------------- #
# Unit: render_with_toc
# --------------------------------------------------------------------------- #
def test_headings_get_ids_and_toc_collected():
    html, toc = render_with_toc("# Intro\n\n## Setup\n\nbody\n")
    assert '<h1 id="intro">Intro</h1>' in html
    assert '<h2 id="setup">Setup</h2>' in html
    assert toc == [
        {"level": 1, "text": "Intro", "id": "intro"},
        {"level": 2, "text": "Setup", "id": "setup"},
    ]


def test_duplicate_headings_get_unique_anchors():
    html, toc = render_with_toc("## Setup\n\n## Setup\n")
    assert [t["id"] for t in toc] == ["setup", "setup-2"]
    assert 'id="setup-2"' in html


def test_deep_headings_are_anchored_but_excluded_from_toc():
    html, toc = render_with_toc("#### Deep heading\n")
    assert toc == []  # h4 below TOC_MAX_LEVEL
    assert 'id="deep-heading"' in html  # still linkable


def test_toc_label_strips_inline_formatting():
    html, toc = render_with_toc("# Hello *world*\n")
    assert toc[0]["text"] == "Hello world"
    assert '<h1 id="hello-world">Hello <em>world</em></h1>' in html


def test_toc_unicode_heading():
    html, toc = render_with_toc("## Mẹo hay\n")
    assert toc[0]["text"] == "Mẹo hay"
    assert toc[0]["id"]  # non-empty unicode-aware anchor
    assert f'id="{toc[0]["id"]}"' in html


# --------------------------------------------------------------------------- #
# Detail page integration
# --------------------------------------------------------------------------- #
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


def test_detail_renders_toc_when_multiple_headings(client):
    client.pm.create({
        "title": "Doc", "tags": [], "category": "G", "status": "published",
        "content": "# One\n\nintro\n\n## Two\n\nmore\n",
    })
    html = client.get("/posts/doc").text
    assert 'class="toc"' in html
    assert 'href="#one"' in html
    assert 'href="#two"' in html
    assert '<h1 id="one">' in html  # anchor target present


def test_detail_no_toc_for_single_heading(client):
    client.pm.create({
        "title": "Short", "tags": [], "category": "G", "status": "published",
        "content": "# Only one\n\nbody\n",
    })
    html = client.get("/posts/short").text
    assert 'class="toc"' not in html
    # heading still rendered + anchored
    assert '<h1 id="only-one">' in html
