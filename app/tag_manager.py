"""TagManager – tag aggregation and a persisted tag index.

Scans the markdown frontmatter directly (cheap, no full Post validation needed)
to count tag usage, and writes a `tags/index.json` mapping {tag: count}.
"""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

import frontmatter as fm_lib

__all__ = ["TagManager"]


class TagManager:
    def __init__(self, posts_dir: Path):
        self.posts_dir = Path(posts_dir)
        self.index_path = self.posts_dir.parent / "tags" / "index.json"

    def all_tags(self) -> dict[str, int]:
        """Return {tag: count} sorted by count descending."""
        counter: Counter = Counter()
        for f in self.posts_dir.glob("*.md"):
            try:
                meta = fm_lib.load(str(f)).metadata
            except Exception:
                continue
            for t in meta.get("tags", []) or []:
                tag = str(t).lower().strip()
                if tag:
                    counter[tag] += 1
        return dict(counter.most_common())

    def rebuild(self) -> dict[str, int]:
        """Recompute the tag index and persist it to `tags/index.json`."""
        tags = self.all_tags()
        self.index_path.parent.mkdir(parents=True, exist_ok=True)
        self.index_path.write_text(
            json.dumps(tags, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return tags
