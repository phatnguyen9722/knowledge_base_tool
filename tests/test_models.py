"""Phase 1 unit tests: Post schema + frontmatter parsing.

Covers the four cases from the Phase 1 checklist:
  - valid post
  - missing required field
  - wrong type
  - UTF-8 (tiếng Việt) content
"""

from datetime import date

import pytest
from pydantic import ValidationError

from app.models import Post, PostStatus
from app.parser import PostParseError, dump_post, parse_string


# --------------------------------------------------------------------------- #
# Model: valid post
# --------------------------------------------------------------------------- #
def test_valid_post():
    post = Post(
        slug="docker-compose-cheatsheet",
        title="Docker Compose Cheatsheet",
        created=date(2024, 1, 15),
        updated=date(2024, 6, 20),
        tags=["Docker", " DevOps ", "commands"],
        category="DevOps",
        status="published",
    )
    assert post.status is PostStatus.published
    assert post.pinned is False
    assert post.summary == ""
    # tags are normalized: lower-cased + stripped
    assert post.tags == ["docker", "devops", "commands"]


def test_tags_normalization_handles_none_and_empties():
    post = Post(
        slug="s",
        title="t",
        created=date(2024, 1, 1),
        updated=date(2024, 1, 1),
        tags=["  ", "Keep", ""],
        category="General",
    )
    assert post.tags == ["keep"]


# --------------------------------------------------------------------------- #
# Model: missing required field
# --------------------------------------------------------------------------- #
def test_missing_required_field():
    with pytest.raises(ValidationError) as exc:
        Post(
            slug="x",
            # title missing
            created=date(2024, 1, 1),
            updated=date(2024, 1, 1),
            tags=["a"],
            category="General",
        )
    assert "title" in str(exc.value)


# --------------------------------------------------------------------------- #
# Model: wrong type
# --------------------------------------------------------------------------- #
def test_wrong_type_status():
    with pytest.raises(ValidationError):
        Post(
            slug="x",
            title="t",
            created=date(2024, 1, 1),
            updated=date(2024, 1, 1),
            tags=["a"],
            category="General",
            status="not-a-valid-status",
        )


def test_wrong_type_date():
    with pytest.raises(ValidationError):
        Post(
            slug="x",
            title="t",
            created="not-a-date",
            updated=date(2024, 1, 1),
            tags=["a"],
            category="General",
        )


# --------------------------------------------------------------------------- #
# Parser: round-trip + UTF-8 (tiếng Việt)
# --------------------------------------------------------------------------- #
VALID_MD = """\
---
title: "Mẹo Docker"
created: 2024-01-15
updated: 2024-06-20
tags: [docker, devops]
category: DevOps
status: published
---

Đây là nội dung tiếng Việt với dấu: ăn, ơ, ư, đ.
"""


def test_parse_string_valid_utf8():
    post = parse_string(VALID_MD, slug="meo-docker")
    assert post.title == "Mẹo Docker"
    assert post.category == "DevOps"
    assert "tiếng Việt" in post.content
    assert "đ" in post.content


def test_parse_string_missing_field_raises():
    bad = """\
---
title: "No dates here"
tags: [a]
category: General
---

body
"""
    with pytest.raises(PostParseError):
        parse_string(bad, slug="bad")


def test_dump_round_trip_preserves_utf8():
    post = parse_string(VALID_MD, slug="meo-docker")
    text = dump_post(post)
    reparsed = parse_string(text, slug="meo-docker")
    assert reparsed.title == post.title
    assert reparsed.content.strip() == post.content.strip()
    assert reparsed.tags == post.tags
    # frontmatter excludes slug/content
    assert "slug:" not in text
