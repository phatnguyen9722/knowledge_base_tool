"""Quick notes — Title / date / content, with pin-to-favorite.

Each note is a markdown file in ``notes/``: frontmatter (title, date, pinned,
created, updated) plus the content body. Pinned notes float to the top of the
list; otherwise notes are ordered by date (newest first).
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

import frontmatter
from slugify import slugify

__all__ = ["Note", "NoteManager", "NOTE_THEMES"]

# Per-note visual styles (background pattern of the card / detail view).
NOTE_THEMES = ["plain", "lines", "dots", "grid", "sticky"]
_DEFAULT_THEME = "plain"


@dataclass
class Note:
    slug: str
    title: str
    date: str = ""
    content: str = ""
    tags: list[str] = field(default_factory=list)
    theme: str = _DEFAULT_THEME
    pinned: bool = False
    created: str = ""
    updated: str = ""


class NoteManager:
    def __init__(self, notes_dir: Path):
        self.notes_dir = Path(notes_dir)
        self.notes_dir.mkdir(parents=True, exist_ok=True)

    def _path(self, slug: str) -> Path:
        return self.notes_dir / f"{slug}.md"

    def _unique_slug(self, title: str) -> str:
        base = slugify(title, allow_unicode=True) or "note"
        slug, n = base, 2
        while self._path(slug).exists():
            slug = f"{base}-{n}"
            n += 1
        return slug

    @staticmethod
    def _norm_tags(tags) -> list[str]:
        return [str(t).lower().strip() for t in (tags or []) if str(t).strip()]

    @staticmethod
    def _norm_theme(theme) -> str:
        t = str(theme or "").lower().strip()
        return t if t in NOTE_THEMES else _DEFAULT_THEME

    def _write(self, note: Note) -> None:
        meta = {
            "title": note.title,
            "date": note.date,
            "tags": note.tags,
            "theme": note.theme,
            "pinned": note.pinned,
            "created": note.created,
            "updated": note.updated,
        }
        fm = frontmatter.Post(note.content, **meta)
        self._path(note.slug).write_text(frontmatter.dumps(fm), encoding="utf-8")

    def create(self, data: dict) -> str:
        today = date.today().isoformat()
        note = Note(
            slug=self._unique_slug(data.get("title", "")),
            title=(data.get("title") or "Untitled").strip(),
            date=(data.get("date") or today).strip(),
            content=data.get("content", ""),
            tags=self._norm_tags(data.get("tags")),
            theme=self._norm_theme(data.get("theme")),
            pinned=bool(data.get("pinned", False)),
            created=today,
            updated=today,
        )
        self._write(note)
        return note.slug

    def read(self, slug: str) -> Note | None:
        path = self._path(slug)
        if not path.exists():
            return None
        fm = frontmatter.load(str(path))
        m = fm.metadata or {}
        return Note(
            slug=slug,
            title=str(m.get("title", slug)),
            date=str(m.get("date", "")),
            content=fm.content,
            tags=self._norm_tags(m.get("tags")),
            theme=self._norm_theme(m.get("theme")),
            pinned=bool(m.get("pinned", False)),
            created=str(m.get("created", "")),
            updated=str(m.get("updated", "")),
        )

    def update(self, slug: str, data: dict) -> str | None:
        note = self.read(slug)
        if not note:
            return None
        note.title = (data.get("title") or note.title).strip()
        note.date = (data.get("date") or note.date).strip()
        note.content = data.get("content", note.content)
        if "tags" in data:
            note.tags = self._norm_tags(data["tags"])
        if "theme" in data:
            note.theme = self._norm_theme(data["theme"])
        if "pinned" in data:
            note.pinned = bool(data["pinned"])
        note.updated = date.today().isoformat()
        self._write(note)
        return slug

    def toggle_pin(self, slug: str) -> bool | None:
        note = self.read(slug)
        if not note:
            return None
        note.pinned = not note.pinned
        note.updated = date.today().isoformat()
        self._write(note)
        return note.pinned

    def delete(self, slug: str) -> bool:
        path = self._path(slug)
        if not path.exists():
            return False
        path.unlink()
        return True

    def list(self, tags: list[str] | None = None, q: str = "") -> list[Note]:
        """Pinned first, then by date (newest first), then title.

        Optional filters: `tags` (note must carry ALL of them) and `q`
        (case-insensitive substring of the title or content).
        """
        notes = []
        for f in self.notes_dir.glob("*.md"):
            note = self.read(f.stem)
            if note:
                notes.append(note)

        wanted = self._norm_tags(tags)
        if wanted:
            notes = [n for n in notes if all(t in n.tags for t in wanted)]
        if q:
            ql = q.strip().lower()
            notes = [n for n in notes
                     if ql in n.title.lower() or ql in n.content.lower()]

        notes.sort(key=lambda n: (n.date, n.title.lower()), reverse=True)
        notes.sort(key=lambda n: n.pinned, reverse=True)
        return notes

    def all_tags(self) -> dict[str, int]:
        """{tag: count} across all notes, most common first."""
        counter: Counter = Counter()
        for f in self.notes_dir.glob("*.md"):
            note = self.read(f.stem)
            if note:
                for t in note.tags:
                    counter[t] += 1
        return dict(counter.most_common())
