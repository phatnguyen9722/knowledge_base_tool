"""Books / novels — collections of chapters.

Layout under ``books/``:

    books/
      harry-potter/
        _collection.md        # collection metadata (title, author, description)
        01-the-boy-who-lived.md
        02-the-vanishing-glass.md

A **collection** must exist before chapters can be added to it. Each chapter is
a markdown file with frontmatter (title, order) plus the chapter body.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

import frontmatter
from slugify import slugify

__all__ = ["Chapter", "Collection", "BookManager"]

_META = "_collection.md"
_RESERVED = {"new"}  # slugs that would collide with routes


@dataclass
class Chapter:
    slug: str
    collection: str
    title: str
    order: int = 0
    created: str = ""
    updated: str = ""
    content: str = ""


@dataclass
class Collection:
    slug: str
    title: str
    author: str = ""
    description: str = ""
    cover: str = ""                              # image URL (e.g. /img/<hash>.png)
    tags: list[str] = field(default_factory=list)
    created: str = ""
    updated: str = ""
    chapters: list[Chapter] = field(default_factory=list)

    @property
    def chapter_count(self) -> int:
        return len(self.chapters)


class BookManager:
    def __init__(self, books_dir: Path):
        self.books_dir = Path(books_dir)
        self.books_dir.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------ #
    # Paths / slugs
    # ------------------------------------------------------------------ #
    def _coll_dir(self, slug: str) -> Path:
        return self.books_dir / slug

    def _meta_path(self, slug: str) -> Path:
        return self._coll_dir(slug) / _META

    def _chapter_path(self, coll: str, slug: str) -> Path:
        return self._coll_dir(coll) / f"{slug}.md"

    def _unique_collection_slug(self, title: str) -> str:
        base = slugify(title, allow_unicode=True) or "collection"
        slug = base if base not in _RESERVED else f"{base}-1"
        n = 2
        while self._coll_dir(slug).exists():
            slug = f"{base}-{n}"
            n += 1
        return slug

    def _unique_chapter_slug(self, coll: str, title: str) -> str:
        base = slugify(title, allow_unicode=True) or "chapter"
        slug = base if base not in _RESERVED else f"{base}-1"
        n = 2
        while self._chapter_path(coll, slug).exists():
            slug = f"{base}-{n}"
            n += 1
        return slug

    # ------------------------------------------------------------------ #
    # Collections
    # ------------------------------------------------------------------ #
    @staticmethod
    def _norm_tags(tags) -> list[str]:
        return [str(t).lower().strip() for t in (tags or []) if str(t).strip()]

    def create_collection(self, data: dict) -> str:
        slug = self._unique_collection_slug(data.get("title", ""))
        today = date.today().isoformat()
        meta = {
            "title": data.get("title", "").strip() or slug,
            "author": data.get("author", "").strip(),
            "description": data.get("description", "").strip(),
            "cover": data.get("cover", "").strip(),
            "tags": self._norm_tags(data.get("tags")),
            "created": today,
            "updated": today,
        }
        self._coll_dir(slug).mkdir(parents=True, exist_ok=True)
        fm = frontmatter.Post("", **meta)
        self._meta_path(slug).write_text(frontmatter.dumps(fm), encoding="utf-8")
        return slug

    def update_collection(self, slug: str, data: dict) -> str | None:
        """Update an existing collection's metadata (preserves created date)."""
        existing = self.read_collection(slug, with_chapters=False)
        if not existing:
            return None
        meta = {
            "title": data.get("title", "").strip() or existing.title,
            "author": data.get("author", existing.author).strip(),
            "description": data.get("description", existing.description).strip(),
            "cover": data.get("cover", existing.cover).strip(),
            "tags": self._norm_tags(data.get("tags")) if "tags" in data else existing.tags,
            "created": existing.created or date.today().isoformat(),
            "updated": date.today().isoformat(),
        }
        fm = frontmatter.Post("", **meta)
        self._meta_path(slug).write_text(frontmatter.dumps(fm), encoding="utf-8")
        return slug

    def read_collection(self, slug: str, with_chapters: bool = True) -> Collection | None:
        meta_path = self._meta_path(slug)
        if not meta_path.exists():
            return None
        fm = frontmatter.load(str(meta_path))
        m = fm.metadata or {}
        coll = Collection(
            slug=slug,
            title=str(m.get("title", slug)),
            author=str(m.get("author", "")),
            description=str(m.get("description", "")),
            cover=str(m.get("cover", "")),
            tags=self._norm_tags(m.get("tags")),
            created=str(m.get("created", "")),
            updated=str(m.get("updated", "")),
        )
        if with_chapters:
            coll.chapters = self.chapters(slug)
        return coll

    def collections(self) -> list[Collection]:
        out = []
        for d in self.books_dir.iterdir():
            if d.is_dir() and (d / _META).exists():
                coll = self.read_collection(d.name)
                if coll:
                    out.append(coll)
        out.sort(key=lambda c: c.title.lower())
        return out

    # ------------------------------------------------------------------ #
    # Chapters
    # ------------------------------------------------------------------ #
    def chapters(self, coll: str) -> list[Chapter]:
        cdir = self._coll_dir(coll)
        if not cdir.exists():
            return []
        items = []
        for f in cdir.glob("*.md"):
            if f.name == _META:
                continue
            ch = self.read_chapter(coll, f.stem)
            if ch:
                items.append(ch)
        items.sort(key=lambda c: (c.order, c.title.lower()))
        return items

    def read_chapter(self, coll: str, slug: str) -> Chapter | None:
        path = self._chapter_path(coll, slug)
        if not path.exists():
            return None
        fm = frontmatter.load(str(path))
        m = fm.metadata or {}
        try:
            order = int(m.get("order", 0) or 0)
        except (ValueError, TypeError):
            order = 0
        return Chapter(
            slug=slug,
            collection=coll,
            title=str(m.get("title", slug)),
            order=order,
            created=str(m.get("created", "")),
            updated=str(m.get("updated", "")),
            content=fm.content,
        )

    def create_chapter(self, coll: str, data: dict) -> str | None:
        if not self._meta_path(coll).exists():
            return None  # collection must exist first
        slug = self._unique_chapter_slug(coll, data.get("title", ""))
        today = date.today().isoformat()
        try:
            order = int(data.get("order", 0) or 0)
        except (ValueError, TypeError):
            order = 0
        meta = {
            "title": data.get("title", "").strip() or slug,
            "order": order,
            "created": today,
            "updated": today,
        }
        fm = frontmatter.Post(data.get("content", ""), **meta)
        self._chapter_path(coll, slug).write_text(frontmatter.dumps(fm), encoding="utf-8")
        return slug
