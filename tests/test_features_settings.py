"""Tests for the Settings → Features toggle panel."""

from pathlib import Path
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


def test_features_panel_in_sidebar_and_dom(client):
    html = client.get("/").text
    assert 'data-panel="features"' in html   # sidebar nav item
    assert 'id="panel-features"' in html      # content panel
    assert 'id="features-panel-list"' in html # list container


def test_topbar_buttons_have_data_feature_app(client):
    html = client.get("/").text
    for app in ("api-docs", "notes", "books", "music", "toeic", "series"):
        assert f'data-feature-app="{app}"' in html


def test_home_cards_have_data_feature_app(client):
    html = client.get("/").text
    for app in ("posts", "series", "books", "toeic", "music", "notes", "api-docs"):
        assert f'data-feature-app="{app}"' in html


def test_no_flash_style_element_present(client):
    html = client.get("/").text
    assert 'id="feature-hide-style"' in html


def test_app_js_has_feature_functions():
    js = Path("static/app.js").read_text(encoding="utf-8")
    assert "FEATURE_LIST" in js
    assert "setFeature" in js
    assert "applyFeatures" in js
    assert "buildFeaturesPanel" in js
    assert "isFeatureEnabled" in js
    assert "kb-features" in js
    assert "data-feature-toggle" in js


def test_toggle_switch_css():
    css = Path("static/style.css").read_text(encoding="utf-8")
    assert ".toggle-switch" in css
    assert ".toggle-slider" in css
    assert ".feature-row" in css
