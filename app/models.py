"""Pydantic data models for the Knowledge Base Tool.

A `Post` is the single domain entity. It maps 1:1 to a markdown file in
`posts/`, where the YAML frontmatter holds the metadata and the body holds the
raw markdown content.
"""

from __future__ import annotations

from datetime import date
from enum import Enum

from pydantic import BaseModel, field_validator


class PostStatus(str, Enum):
    """Publication state of a post."""

    published = "published"
    draft = "draft"
    archived = "archived"


class Post(BaseModel):
    """A single knowledge-base entry.

    `slug` and `content` are derived/stored separately from the frontmatter:
    the slug comes from the filename, and the content is the markdown body.
    Everything else lives in the YAML frontmatter.
    """

    slug: str
    title: str
    created: date
    updated: date
    tags: list[str]
    category: str
    status: PostStatus = PostStatus.published
    pinned: bool = False
    summary: str = ""
    series: str = ""           # name of the series this post belongs to ("" = none)
    series_order: int = 0      # position within the series (lower = earlier)
    content: str = ""  # raw markdown body

    @field_validator("tags", mode="before")
    @classmethod
    def normalize_tags(cls, v):
        """Lower-case, strip and drop empty tags. Accepts None -> []."""
        if not v:
            return []
        return [t.lower().strip() for t in v if str(t).strip()]
