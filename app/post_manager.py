"""PostManager – CRUD over markdown posts, with FTS5 auto-indexing.

The markdown files in `posts_dir` are the source of truth. Every write also
updates the SQLite FTS5 index so search stays consistent. Parsing/serialization
is delegated to `app.parser` (built in Phase 1).
"""

from __future__ import annotations

from datetime import date
from pathlib import Path

from slugify import slugify

from .hooks import emit
from .models import Post
from .parser import dump_post, parse_post
from .search import SearchEngine

__all__ = ["PostManager"]


class PostManager:
    def __init__(self, posts_dir: Path, db_path: Path):
        self.posts_dir = Path(posts_dir)
        self.posts_dir.mkdir(parents=True, exist_ok=True)
        self.search = SearchEngine(db_path)

    # ------------------------------------------------------------------ #
    # Paths
    # ------------------------------------------------------------------ #
    def _path(self, slug: str) -> Path:
        return self.posts_dir / f"{slug}.md"

    def _unique_slug(self, title: str) -> str:
        """Slugify a title (unicode-aware) and disambiguate collisions."""
        base = slugify(title, allow_unicode=True) or "post"
        slug = base
        n = 2
        while self._path(slug).exists():
            slug = f"{base}-{n}"
            n += 1
        return slug

    # ------------------------------------------------------------------ #
    # CRUD
    # ------------------------------------------------------------------ #
    def create(self, data: dict) -> Post:
        data = dict(data)
        slug = self._unique_slug(data.get("title", ""))
        data.setdefault("created", date.today())
        data.setdefault("updated", date.today())
        post = Post(slug=slug, **data)
        self._write(post)
        self.search.index(post)
        emit("on_post_created", post)
        return post

    def read(self, slug: str) -> Post | None:
        path = self._path(slug)
        if not path.exists():
            return None
        return parse_post(path)

    def update(self, slug: str, data: dict) -> Post | None:
        post = self.read(slug)
        if not post:
            return None
        data = dict(data)
        data.setdefault("updated", date.today())
        # Re-validate through the model so types (e.g. status enum) are coerced,
        # rather than model_copy which would store raw strings unchanged.
        updated = Post(**{**post.model_dump(), **data})
        self._write(updated)
        self.search.index(updated)
        emit("on_post_updated", updated)
        return updated

    def delete(self, slug: str) -> bool:
        path = self._path(slug)
        if not path.exists():
            return False
        path.unlink()
        self.search.remove(slug)
        emit("on_post_deleted", slug)
        return True

    def list(self, status: str | None = None) -> list[Post]:
        """List posts, pinned first then most-recently-updated."""
        posts: list[Post] = []
        for f in self.posts_dir.glob("*.md"):
            post = self.read(f.stem)
            if post and (status is None or post.status == status):
                posts.append(post)
        # Stable sorts, applied last-key-first: newest updated, then pinned on top.
        posts.sort(key=lambda p: p.updated, reverse=True)
        posts.sort(key=lambda p: p.pinned, reverse=True)
        return posts

    def categories(self) -> dict[str, int]:
        """Return {category: count} sorted by count desc (cheap frontmatter scan)."""
        import frontmatter as fm_lib
        from collections import Counter

        counter: Counter = Counter()
        for f in self.posts_dir.glob("*.md"):
            try:
                meta = fm_lib.load(str(f)).metadata
            except Exception:
                continue
            cat = str(meta.get("category", "")).strip()
            if cat:
                counter[cat] += 1
        return dict(counter.most_common())

    def series(self, name: str) -> list[Post]:
        """Return all posts in a named series, ordered by series_order then date."""
        if not name:
            return []
        members = [
            p for p in (self.read(f.stem) for f in self.posts_dir.glob("*.md"))
            if p and p.series == name
        ]
        members.sort(key=lambda p: (p.series_order, p.created, p.title))
        return members

    def all_series(self) -> list[dict]:
        """Return every distinct series as {name, count, first_slug, latest}.

        `first_slug` is the earliest part (entry point); `latest` is the most
        recent update across the series. Sorted by name (A–Z).
        """
        groups: dict[str, list[Post]] = {}
        for f in self.posts_dir.glob("*.md"):
            post = self.read(f.stem)
            if post and post.series:
                groups.setdefault(post.series, []).append(post)

        out = []
        for name, members in groups.items():
            members.sort(key=lambda p: (p.series_order, p.created, p.title))
            out.append({
                "name": name,
                "count": len(members),
                "first_slug": members[0].slug,
                "latest": max(p.updated for p in members),
            })
        out.sort(key=lambda s: s["name"].lower())
        return out

    def rebuild_index(self) -> int:
        """Re-index every post on disk. Returns the count indexed."""
        posts = [self.read(f.stem) for f in self.posts_dir.glob("*.md")]
        posts = [p for p in posts if p]
        self.search.rebuild(posts)
        return len(posts)

    # ------------------------------------------------------------------ #
    # Persistence
    # ------------------------------------------------------------------ #
    def _write(self, post: Post):
        self.posts_dir.mkdir(parents=True, exist_ok=True)
        self._path(post.slug).write_text(dump_post(post), encoding="utf-8")
