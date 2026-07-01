"""Phase 2 integration tests: PostManager + SearchEngine + TagManager.

Covers the checklist cases:
  - CRUD round-trip
  - search recall
  - UTF-8 (tiếng Việt)
"""

import json
from datetime import date

import pytest

from app.post_manager import PostManager
from app.tag_manager import TagManager


@pytest.fixture
def pm(tmp_path):
    """A PostManager rooted in an isolated temp dir."""
    posts_dir = tmp_path / "posts"
    db_path = tmp_path / ".kb" / "search.db"
    manager = PostManager(posts_dir, db_path)
    yield manager
    manager.search.close()


def _new(pm, title, **over):
    data = {
        "title": title,
        "tags": ["docker", "devops"],
        "category": "DevOps",
        "status": "published",
    }
    data.update(over)
    return pm.create(data)


# --------------------------------------------------------------------------- #
# CRUD round-trip
# --------------------------------------------------------------------------- #
def test_create_then_read_round_trip(pm):
    post = _new(pm, "Docker Compose Cheatsheet", summary="cheats")
    assert post.slug == "docker-compose-cheatsheet"
    assert pm._path(post.slug).exists()

    read = pm.read(post.slug)
    assert read is not None
    assert read.title == "Docker Compose Cheatsheet"
    assert read.tags == ["docker", "devops"]
    assert read.summary == "cheats"


def test_update_persists_and_reindexes(pm):
    post = _new(pm, "Original Title")
    updated = pm.update(post.slug, {"title": "Edited Title", "tags": ["k8s"]})
    assert updated.title == "Edited Title"

    read = pm.read(post.slug)
    assert read.title == "Edited Title"
    assert read.tags == ["k8s"]
    # search reflects the update
    assert post.slug in pm.search.search("Edited")
    assert pm.search.search("Original") == []


def test_delete_removes_file_and_index(pm):
    post = _new(pm, "To Be Deleted")
    assert pm.delete(post.slug) is True
    assert not pm._path(post.slug).exists()
    assert pm.read(post.slug) is None
    assert pm.search.search("Deleted") == []
    # deleting again is a no-op
    assert pm.delete(post.slug) is False


def test_slug_collision_disambiguates(pm):
    a = _new(pm, "Same Title")
    b = _new(pm, "Same Title")
    assert a.slug == "same-title"
    assert b.slug == "same-title-2"
    assert pm._path(a.slug).exists() and pm._path(b.slug).exists()


def test_list_pinned_first_then_newest(pm):
    _new(pm, "Old", updated=date(2024, 1, 1))
    _new(pm, "New", updated=date(2024, 12, 31))
    _new(pm, "Pinned Old", updated=date(2023, 1, 1), pinned=True)

    titles = [p.title for p in pm.list()]
    assert titles[0] == "Pinned Old"          # pinned floats to top
    assert titles[1:] == ["New", "Old"]       # then newest-updated first


# --------------------------------------------------------------------------- #
# Search recall + snippet
# --------------------------------------------------------------------------- #
def test_search_recall_by_content_and_tag(pm):
    _new(pm, "Kubernetes Guide", tags=["k8s", "ops"], category="Ops",
         content="Scaling pods with kubectl.")
    _new(pm, "Docker Guide", tags=["docker"], category="DevOps",
         content="Building images.")

    assert pm.search.search("kubectl") == [
        s for s in pm.search.search("kubectl")
    ]  # deterministic
    assert "kubernetes-guide" in pm.search.search("pods")
    # tag filter narrows results
    assert pm.search.search("Guide", tag="docker") == ["docker-guide"]


def test_search_snippet_highlights_match(pm):
    _new(pm, "Highlight Me", content="the special keyword appears here")
    hits = pm.search.search_snippets("keyword")
    assert hits and hits[0]["slug"] == "highlight-me"
    assert "<mark>" in hits[0]["snippet"]


# --------------------------------------------------------------------------- #
# UTF-8 (tiếng Việt)
# --------------------------------------------------------------------------- #
def test_utf8_vietnamese_round_trip_and_search(pm):
    post = pm.create({
        "title": "Mẹo Docker tiếng Việt",
        "tags": ["Tiếng Việt", "docker"],
        "category": "Ghi chú",
        "status": "published",
        "content": "Nội dung có dấu: ăn, ơ, ư, đường.",
    })
    assert post.slug  # unicode slug produced
    read = pm.read(post.slug)
    assert read.title == "Mẹo Docker tiếng Việt"
    assert "đường" in read.content
    assert "tiếng việt" in read.tags
    # full-text search finds vietnamese content
    assert post.slug in pm.search.search("đường")


# --------------------------------------------------------------------------- #
# TagManager
# --------------------------------------------------------------------------- #
def test_tag_manager_counts_and_persists(tmp_path):
    posts_dir = tmp_path / "posts"
    pm = PostManager(posts_dir, tmp_path / ".kb" / "search.db")
    _new(pm, "A", tags=["docker", "devops"])
    _new(pm, "B", tags=["docker"])
    pm.search.close()

    tm = TagManager(posts_dir)
    tags = tm.all_tags()
    assert tags["docker"] == 2
    assert tags["devops"] == 1
    # most_common ordering: docker first
    assert list(tags.keys())[0] == "docker"

    written = tm.rebuild()
    assert tm.index_path.exists()
    on_disk = json.loads(tm.index_path.read_text(encoding="utf-8"))
    assert on_disk == written == tags
