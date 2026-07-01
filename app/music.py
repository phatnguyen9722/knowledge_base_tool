"""Music library — imported .mp3 files with editable markdown metadata.

Each track is stored as two files in ``music/``:

    music/<slug>.mp3     the audio
    music/<slug>.md      frontmatter metadata (title, author, year, type, album)
                         + an optional markdown notes body

Importing an .mp3 saves the audio and generates the markdown sidecar (title
defaults to the filename); the user then edits the metadata.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

import frontmatter
from slugify import slugify

__all__ = ["Track", "Playlist", "MusicManager"]


@dataclass
class Track:
    slug: str
    title: str
    author: str = ""
    year: str = ""
    type: str = ""          # genre / category
    album: str = ""
    cover: str = ""         # cover image URL (e.g. /img/<hash>.png)
    notes: str = ""         # short note (frontmatter)
    lyrics: str = ""        # full lyrics (markdown body, line breaks preserved)
    audio_url: str = ""     # /audio/<slug>.mp3
    created: str = ""
    updated: str = ""


@dataclass
class Playlist:
    slug: str
    title: str
    description: str = ""
    track_slugs: list[str] = field(default_factory=list)
    tracks: list[Track] = field(default_factory=list)   # resolved
    created: str = ""
    updated: str = ""

    @property
    def count(self) -> int:
        return len(self.tracks)


class MusicManager:
    def __init__(self, music_dir: Path):
        self.music_dir = Path(music_dir)
        self.music_dir.mkdir(parents=True, exist_ok=True)
        self.playlists_dir = self.music_dir / "playlists"
        self.playlists_dir.mkdir(parents=True, exist_ok=True)

    def _md_path(self, slug: str) -> Path:
        return self.music_dir / f"{slug}.md"

    def _mp3_path(self, slug: str) -> Path:
        return self.music_dir / f"{slug}.mp3"

    def _unique_slug(self, name: str) -> str:
        base = slugify(name, allow_unicode=True) or "track"
        slug, n = base, 2
        while self._md_path(slug).exists() or self._mp3_path(slug).exists():
            slug = f"{base}-{n}"
            n += 1
        return slug

    # ------------------------------------------------------------------ #
    # Import / write
    # ------------------------------------------------------------------ #
    def import_track(self, filename: str, data: bytes) -> str:
        """Save the uploaded mp3 + generate its metadata sidecar. Returns slug."""
        stem = Path(filename).stem or "track"
        slug = self._unique_slug(stem)
        self.music_dir.mkdir(parents=True, exist_ok=True)
        self._mp3_path(slug).write_bytes(data)
        today = date.today().isoformat()
        meta = {
            "title": stem,
            "author": "",
            "year": "",
            "type": "",
            "album": "",
            "cover": "",
            "notes": "",
            "created": today,
            "updated": today,
        }
        fm = frontmatter.Post("", **meta)  # empty body = no lyrics yet
        self._md_path(slug).write_text(frontmatter.dumps(fm), encoding="utf-8")
        return slug

    def update(self, slug: str, data: dict) -> str | None:
        existing = self.read(slug)
        if not existing:
            return None
        meta = {
            "title": (data.get("title") or existing.title).strip(),
            "author": data.get("author", existing.author).strip(),
            "year": str(data.get("year", existing.year)).strip(),
            "type": data.get("type", existing.type).strip(),
            "album": data.get("album", existing.album).strip(),
            "cover": data.get("cover", existing.cover).strip(),
            "notes": data.get("notes", existing.notes).strip(),
            "created": existing.created or date.today().isoformat(),
            "updated": date.today().isoformat(),
        }
        # The markdown body holds the lyrics (line breaks preserved verbatim).
        lyrics = data.get("lyrics", existing.lyrics)
        fm = frontmatter.Post(lyrics, **meta)
        self._md_path(slug).write_text(frontmatter.dumps(fm), encoding="utf-8")
        return slug

    def delete(self, slug: str) -> bool:
        md, mp3 = self._md_path(slug), self._mp3_path(slug)
        if not md.exists() and not mp3.exists():
            return False
        for p in (md, mp3):
            if p.exists():
                p.unlink()
        return True

    # ------------------------------------------------------------------ #
    # Read
    # ------------------------------------------------------------------ #
    def read(self, slug: str) -> Track | None:
        md = self._md_path(slug)
        if not md.exists():
            return None
        fm = frontmatter.load(str(md))
        m = fm.metadata or {}
        audio_url = f"/audio/{slug}.mp3" if self._mp3_path(slug).exists() else ""
        return Track(
            slug=slug,
            title=str(m.get("title", slug)),
            author=str(m.get("author", "")),
            year=str(m.get("year", "")),
            type=str(m.get("type", "")),
            album=str(m.get("album", "")),
            cover=str(m.get("cover", "")),
            notes=str(m.get("notes", "")),
            lyrics=fm.content,
            audio_url=audio_url,
            created=str(m.get("created", "")),
            updated=str(m.get("updated", "")),
        )

    def list(self) -> list[Track]:
        tracks = []
        for f in self.music_dir.glob("*.md"):
            t = self.read(f.stem)
            if t:
                tracks.append(t)
        tracks.sort(key=lambda t: t.title.lower())
        return tracks

    # ------------------------------------------------------------------ #
    # Playlists
    # ------------------------------------------------------------------ #
    def _pl_path(self, slug: str) -> Path:
        return self.playlists_dir / f"{slug}.md"

    def _unique_pl_slug(self, title: str) -> str:
        base = slugify(title, allow_unicode=True) or "playlist"
        slug, n = base, 2
        while self._pl_path(slug).exists():
            slug = f"{base}-{n}"
            n += 1
        return slug

    def _write_playlist(self, pl: Playlist) -> None:
        meta = {
            "title": pl.title,
            "description": pl.description,
            "tracks": pl.track_slugs,
            "created": pl.created,
            "updated": pl.updated,
        }
        fm = frontmatter.Post("", **meta)
        self._pl_path(pl.slug).write_text(frontmatter.dumps(fm), encoding="utf-8")

    def create_playlist(self, data: dict) -> str:
        today = date.today().isoformat()
        pl = Playlist(
            slug=self._unique_pl_slug(data.get("title", "")),
            title=(data.get("title") or "Untitled").strip(),
            description=(data.get("description", "")).strip(),
            track_slugs=list(data.get("track_slugs", [])),
            created=today,
            updated=today,
        )
        self._write_playlist(pl)
        return pl.slug

    def read_playlist(self, slug: str, resolve: bool = True) -> Playlist | None:
        path = self._pl_path(slug)
        if not path.exists():
            return None
        fm = frontmatter.load(str(path))
        m = fm.metadata or {}
        slugs = [str(s) for s in (m.get("tracks") or [])]
        pl = Playlist(
            slug=slug,
            title=str(m.get("title", slug)),
            description=str(m.get("description", "")),
            track_slugs=slugs,
            created=str(m.get("created", "")),
            updated=str(m.get("updated", "")),
        )
        if resolve:
            # keep playlist order; drop any tracks that no longer exist
            pl.tracks = [t for t in (self.read(s) for s in slugs) if t]
        return pl

    def list_playlists(self) -> list[Playlist]:
        out = []
        for f in self.playlists_dir.glob("*.md"):
            pl = self.read_playlist(f.stem)
            if pl:
                out.append(pl)
        out.sort(key=lambda p: p.title.lower())
        return out

    def add_to_playlist(self, slug: str, track_slug: str) -> bool:
        pl = self.read_playlist(slug, resolve=False)
        if not pl or not self.read(track_slug):
            return False
        if track_slug not in pl.track_slugs:
            pl.track_slugs.append(track_slug)
            pl.updated = date.today().isoformat()
            self._write_playlist(pl)
        return True

    def move_track(self, slug: str, track_slug: str, direction: str) -> bool:
        """Move a track one step `up` or `down` within the playlist order."""
        pl = self.read_playlist(slug, resolve=False)
        if not pl or track_slug not in pl.track_slugs:
            return False
        i = pl.track_slugs.index(track_slug)
        j = i - 1 if direction == "up" else i + 1
        if j < 0 or j >= len(pl.track_slugs):
            return True  # already at the edge — no-op
        pl.track_slugs[i], pl.track_slugs[j] = pl.track_slugs[j], pl.track_slugs[i]
        pl.updated = date.today().isoformat()
        self._write_playlist(pl)
        return True

    def remove_from_playlist(self, slug: str, track_slug: str) -> bool:
        pl = self.read_playlist(slug, resolve=False)
        if not pl:
            return False
        if track_slug in pl.track_slugs:
            pl.track_slugs.remove(track_slug)
            pl.updated = date.today().isoformat()
            self._write_playlist(pl)
        return True

    def delete_playlist(self, slug: str) -> bool:
        path = self._pl_path(slug)
        if not path.exists():
            return False
        path.unlink()
        return True
