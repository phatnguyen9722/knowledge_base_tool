"""Frontmatter parsing and validation.

Bridges `python-frontmatter` (file <-> YAML metadata + body) and the Pydantic
`Post` model (validation + normalization). Phase 2's PostManager will build on
these helpers; Phase 1 only needs round-trippable, validated parsing.
"""

from __future__ import annotations

from pathlib import Path

import frontmatter
from pydantic import ValidationError

from .models import Post

__all__ = ["parse_post", "parse_string", "dump_post", "PostParseError"]


class PostParseError(ValueError):
    """Raised when a markdown file cannot be parsed into a valid Post."""


def parse_string(text: str, slug: str) -> Post:
    """Parse raw markdown-with-frontmatter text into a validated Post."""
    fm = frontmatter.loads(text)
    try:
        return Post(slug=slug, content=fm.content, **fm.metadata)
    except ValidationError as exc:
        raise PostParseError(f"Invalid post '{slug}': {exc}") from exc


def parse_post(path: str | Path) -> Post:
    """Load a `.md` file and parse it into a validated Post.

    The slug is taken from the filename stem.
    """
    path = Path(path)
    if not path.exists():
        raise PostParseError(f"File not found: {path}")
    fm = frontmatter.load(str(path))
    try:
        return Post(slug=path.stem, content=fm.content, **fm.metadata)
    except ValidationError as exc:
        raise PostParseError(f"Invalid post '{path}': {exc}") from exc


def dump_post(post: Post) -> str:
    """Serialize a Post back to markdown-with-frontmatter text.

    `slug` and `content` are excluded from the frontmatter: the slug lives in
    the filename and the content is the body.
    """
    meta = post.model_dump(exclude={"content", "slug"}, mode="json")
    fm = frontmatter.Post(post.content, **meta)
    return frontmatter.dumps(fm)
