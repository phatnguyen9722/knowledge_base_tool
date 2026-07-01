"""Tests for the Series index page (/series) and name sorting."""

import re

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
        c.pm = pm
        yield c
    pm.search.close()


def _mk(pm, title, series, order=1):
    return pm.create({"title": title, "tags": [], "category": "G",
                      "status": "published", "series": series, "series_order": order})


def _series_order_in_html(html):
    # series names render as card titles; grab them in document order
    return re.findall(r'card-title"><a href="/posts/[^"]+">([^<]+)</a>', html)


def test_all_series_groups_and_counts(client):
    _mk(client.pm, "Zebra P1", "Zebra", 1)
    _mk(client.pm, "Zebra P2", "Zebra", 2)
    _mk(client.pm, "Apple P1", "Apple", 1)
    _mk(client.pm, "Loner", "")  # no series

    series = client.pm.all_series()
    names = [s["name"] for s in series]
    assert names == ["Apple", "Zebra"]            # default A-Z
    zebra = next(s for s in series if s["name"] == "Zebra")
    assert zebra["count"] == 2
    assert zebra["first_slug"] == "zebra-p1"


def test_series_button_in_topbar(client):
    html = client.get("/").text
    assert 'href="/series"' in html


def test_series_page_sort_az(client):
    _mk(client.pm, "Mango Intro", "Mango")
    _mk(client.pm, "Apple Intro", "Apple")
    _mk(client.pm, "Zebra Intro", "Zebra")

    html = client.get("/series?sort=az").text
    assert _series_order_in_html(html) == ["Apple", "Mango", "Zebra"]
    # az chip active
    assert 'href="/series?sort=az"' in html


def test_series_page_sort_za(client):
    _mk(client.pm, "Mango Intro", "Mango")
    _mk(client.pm, "Apple Intro", "Apple")
    _mk(client.pm, "Zebra Intro", "Zebra")

    html = client.get("/series?sort=za").text
    assert _series_order_in_html(html) == ["Zebra", "Mango", "Apple"]


def test_series_page_empty_state(client):
    html = client.get("/series").text
    assert "No series yet" in html


def test_series_page_bad_sort_defaults_az(client):
    _mk(client.pm, "Apple Intro", "Apple")
    _mk(client.pm, "Zebra Intro", "Zebra")
    html = client.get("/series?sort=bogus").text
    assert _series_order_in_html(html) == ["Apple", "Zebra"]
