"""Tests for the Settings UI + theme picker (Light/Dark/Ocean/Clay)."""

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


def test_settings_button_and_theme_options_render(client):
    html = client.get("/").text
    assert 'id="settings-btn"' in html
    assert 'id="settings-modal"' in html
    for theme in ["vodka", "midnight", "sapphire", "aegean", "champagne", "rose", "amethyst", "dracula", "reverie"]:
        assert f'data-theme-set="{theme}"' in html
    # no-flash loader present
    assert 'localStorage.getItem("kb-theme")' in html


def test_all_themes_defined_in_css():
    css = (Path("static") / "style.css").read_text(encoding="utf-8")
    # non-default palettes (vodka is the :root default, no [data-theme] block)
    for theme in ["midnight", "sapphire", "aegean", "champagne", "rose", "amethyst", "dracula", "reverie"]:
        assert f'[data-theme="{theme}"]' in css
    # swatches for the picker (incl. vodka)
    for sw in [".sw-vodka", ".sw-midnight", ".sw-sapphire", ".sw-aegean",
               ".sw-champagne", ".sw-rose", ".sw-amethyst", ".sw-dracula", ".sw-reverie"]:
        assert sw in css
