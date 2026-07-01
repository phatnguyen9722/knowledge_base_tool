"""Bookmarks — save, organise, and filter URLs.

Each bookmark is a markdown file in ``bookmarks/``:

    ---
    title: "GitHub"
    url: "https://github.com"
    description: "Where the world builds software"
    tags: [git, devtools]
    category: Dev Tools
    pinned: false
    created: 2026-06-30
    updated: 2026-06-30
    ---

    Optional markdown notes about this bookmark.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from urllib.parse import urlparse

import frontmatter
from slugify import slugify

__all__ = ["Bookmark", "BookmarksManager"]


@dataclass
class Bookmark:
    slug: str
    title: str
    url: str
    description: str = ""
    tags: list[str] = field(default_factory=list)
    category: str = ""
    pinned: bool = False
    notes: str = ""        # markdown body
    created: str = ""
    updated: str = ""

    @property
    def domain(self) -> str:
        try:
            return urlparse(self.url).netloc or self.url
        except Exception:
            return self.url

    @property
    def favicon_url(self) -> str:
        try:
            parsed = urlparse(self.url)
            if parsed.scheme and parsed.netloc:
                return f"{parsed.scheme}://{parsed.netloc}/favicon.ico"
        except Exception:
            pass
        return ""


class BookmarksManager:
    def __init__(self, bookmarks_dir: Path):
        self.bookmarks_dir = Path(bookmarks_dir)
        self.bookmarks_dir.mkdir(parents=True, exist_ok=True)

    def _path(self, slug: str) -> Path:
        return self.bookmarks_dir / f"{slug}.md"

    def _unique_slug(self, title: str) -> str:
        base = slugify(title, allow_unicode=True) or "bookmark"
        slug, n = base, 2
        while self._path(slug).exists():
            slug = f"{base}-{n}"
            n += 1
        return slug

    @staticmethod
    def _norm_tags(tags) -> list[str]:
        return [str(t).lower().strip() for t in (tags or []) if str(t).strip()]

    def _write(self, bm: Bookmark) -> None:
        meta = {
            "title": bm.title,
            "url": bm.url,
            "description": bm.description,
            "tags": bm.tags,
            "category": bm.category,
            "pinned": bm.pinned,
            "created": bm.created,
            "updated": bm.updated,
        }
        fm = frontmatter.Post(bm.notes, **meta)
        self._path(bm.slug).write_text(frontmatter.dumps(fm), encoding="utf-8")

    # ------------------------------------------------------------------ #
    # CRUD
    # ------------------------------------------------------------------ #
    def create(self, data: dict) -> str:
        today = date.today().isoformat()
        bm = Bookmark(
            slug=self._unique_slug(data.get("title", data.get("url", ""))),
            title=(data.get("title") or data.get("url", "")).strip(),
            url=data.get("url", "").strip(),
            description=data.get("description", "").strip(),
            tags=self._norm_tags(data.get("tags")),
            category=data.get("category", "").strip(),
            pinned=bool(data.get("pinned", False)),
            notes=data.get("notes", ""),
            created=today,
            updated=today,
        )
        self._write(bm)
        return bm.slug

    def read(self, slug: str) -> Bookmark | None:
        path = self._path(slug)
        if not path.exists():
            return None
        fm = frontmatter.load(str(path))
        m = fm.metadata or {}
        return Bookmark(
            slug=slug,
            title=str(m.get("title", slug)),
            url=str(m.get("url", "")),
            description=str(m.get("description", "")),
            tags=self._norm_tags(m.get("tags")),
            category=str(m.get("category", "")),
            pinned=bool(m.get("pinned", False)),
            notes=fm.content,
            created=str(m.get("created", "")),
            updated=str(m.get("updated", "")),
        )

    def update(self, slug: str, data: dict) -> str | None:
        bm = self.read(slug)
        if not bm:
            return None
        bm.title = (data.get("title") or bm.title).strip()
        bm.url = (data.get("url") or bm.url).strip()
        bm.description = data.get("description", bm.description).strip()
        bm.tags = self._norm_tags(data.get("tags")) if "tags" in data else bm.tags
        bm.category = data.get("category", bm.category).strip()
        bm.notes = data.get("notes", bm.notes)
        if "pinned" in data:
            bm.pinned = bool(data["pinned"])
        bm.updated = date.today().isoformat()
        self._write(bm)
        return slug

    def toggle_pin(self, slug: str) -> bool | None:
        bm = self.read(slug)
        if not bm:
            return None
        bm.pinned = not bm.pinned
        bm.updated = date.today().isoformat()
        self._write(bm)
        return bm.pinned

    def delete(self, slug: str) -> bool:
        path = self._path(slug)
        if not path.exists():
            return False
        path.unlink()
        return True

    # ------------------------------------------------------------------ #
    # List / filter
    # ------------------------------------------------------------------ #
    def list(
        self,
        tags: list[str] | None = None,
        q: str = "",
        category: str = "",
    ) -> list[Bookmark]:
        """Pinned first, then newest created. Optional tag-AND / text / category filters."""
        items: list[Bookmark] = []
        for f in self.bookmarks_dir.glob("*.md"):
            bm = self.read(f.stem)
            if bm:
                items.append(bm)

        if tags:
            items = [b for b in items if all(t in b.tags for t in tags)]
        if category:
            items = [b for b in items if b.category == category]
        if q:
            ql = q.strip().lower()
            items = [
                b for b in items
                if ql in b.title.lower()
                or ql in b.url.lower()
                or ql in b.description.lower()
                or ql in b.notes.lower()
            ]

        items.sort(key=lambda b: b.created, reverse=True)
        items.sort(key=lambda b: b.pinned, reverse=True)
        return items

    def all_tags(self) -> dict[str, int]:
        counter: Counter = Counter()
        for f in self.bookmarks_dir.glob("*.md"):
            bm = self.read(f.stem)
            if bm:
                for t in bm.tags:
                    counter[t] += 1
        return dict(counter.most_common())

    def all_categories(self) -> list[str]:
        cats: set[str] = set()
        for f in self.bookmarks_dir.glob("*.md"):
            bm = self.read(f.stem)
            if bm and bm.category:
                cats.add(bm.category)
        return sorted(cats)
