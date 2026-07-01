"""SQLite FTS5 full-text search engine.

Stores a denormalized copy of each post (title/content/tags/category) in an
FTS5 virtual table keyed by slug. The markdown files remain the source of
truth; this index is rebuildable from them at any time.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

from .models import Post

__all__ = ["SearchEngine"]


class SearchEngine:
    def __init__(self, db_path: Path):
        db_path = Path(db_path)
        db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(str(db_path), check_same_thread=False)
        self._init()

    def _init(self):
        self.conn.execute(
            """
            CREATE VIRTUAL TABLE IF NOT EXISTS posts_fts
            USING fts5(slug UNINDEXED, title, content, tags, category)
            """
        )
        self.conn.commit()

    # ------------------------------------------------------------------ #
    # Write path
    # ------------------------------------------------------------------ #
    def index(self, post: Post):
        """Insert-or-replace a single post in the index."""
        self.conn.execute("DELETE FROM posts_fts WHERE slug = ?", (post.slug,))
        self.conn.execute(
            "INSERT INTO posts_fts VALUES (?, ?, ?, ?, ?)",
            (
                post.slug,
                post.title,
                post.content,
                " ".join(post.tags),
                post.category,
            ),
        )
        self.conn.commit()

    def remove(self, slug: str):
        self.conn.execute("DELETE FROM posts_fts WHERE slug = ?", (slug,))
        self.conn.commit()

    def rebuild(self, posts: list[Post]):
        """Wipe and re-populate the whole index from a list of posts."""
        self.conn.execute("DELETE FROM posts_fts")
        self.conn.executemany(
            "INSERT INTO posts_fts VALUES (?, ?, ?, ?, ?)",
            [
                (p.slug, p.title, p.content, " ".join(p.tags), p.category)
                for p in posts
            ],
        )
        self.conn.commit()

    # ------------------------------------------------------------------ #
    # Read path
    # ------------------------------------------------------------------ #
    @staticmethod
    def _filters(
        tag: str | None,
        tags: list[str] | None,
        category: str | None,
    ) -> tuple[str, list[str]]:
        """Build the AND-filter SQL fragment + params for tags/category.

        Multiple tags are combined with AND logic (a post must carry all of
        them). `tag` (single) is merged into `tags` for back-compat.
        """
        clause = ""
        params: list[str] = []
        all_tags = list(tags or [])
        if tag:
            all_tags.append(tag)
        for t in all_tags:
            if t:
                clause += " AND tags LIKE ?"
                params.append(f"%{t}%")
        if category:
            clause += " AND category = ?"
            params.append(category)
        return clause, params

    def search(
        self,
        query: str,
        tag: str | None = None,
        category: str | None = None,
        tags: list[str] | None = None,
    ) -> list[str]:
        """Return matching slugs ranked by FTS5 relevance."""
        if not query:
            return []
        clause, extra = self._filters(tag, tags, category)
        sql = "SELECT slug FROM posts_fts WHERE posts_fts MATCH ?" + clause + " ORDER BY rank"
        rows = self.conn.execute(sql, [query, *extra]).fetchall()
        return [r[0] for r in rows]

    def search_snippets(
        self,
        query: str,
        tag: str | None = None,
        category: str | None = None,
        tags: list[str] | None = None,
        limit: int = 50,
    ) -> list[dict]:
        """Return matches with a highlighted snippet of the content.

        Each item: {"slug", "title", "snippet"} where `snippet` wraps matched
        terms in <mark>…</mark> with an ellipsis for elided text.
        """
        if not query:
            return []
        clause, extra = self._filters(tag, tags, category)
        # snippet(table, column_index, start_mark, end_mark, ellipsis, tokens)
        sql = (
            "SELECT slug, title, "
            "snippet(posts_fts, 2, '<mark>', '</mark>', '…', 12) AS snip "
            "FROM posts_fts WHERE posts_fts MATCH ?"
            + clause
            + " ORDER BY rank LIMIT ?"
        )
        rows = self.conn.execute(sql, [query, *extra, limit]).fetchall()
        return [{"slug": r[0], "title": r[1], "snippet": r[2]} for r in rows]

    def close(self):
        self.conn.close()
