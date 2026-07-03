"""Books / novels — collections of chapters.

Layout under ``books/``:

    books/
      harry-potter/
        _collection.md        # collection metadata (title, author, description)
        01-the-boy-who-lived.md
        02-the-vanishing-glass.md
        resources/
          my-book.pdf         # imported binary book files
          another.epub

A **collection** must exist before chapters can be added to it. Each chapter is
a markdown file with frontmatter (title, order) plus the chapter body.

Resource books are binary files (PDF, EPUB, MOBI, CBZ, FB2, XPS) stored in
``books/<coll>/resources/`` and rendered on demand via PyMuPDF.
"""

from __future__ import annotations

import io
import mimetypes
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

import frontmatter
from slugify import slugify

__all__ = ["Chapter", "Collection", "ResourceBook", "BookManager"]

# File formats supported for import
RESOURCE_EXTENSIONS = {".pdf", ".epub", ".mobi", ".cbz", ".fb2", ".xps", ".azw", ".azw3"}

# Formats where we render as page images (binary/visual formats)
IMAGE_RENDER_FORMATS = {".pdf", ".cbz", ".xps"}

# Formats where we extract flowing text/HTML
TEXT_RENDER_FORMATS = {".epub", ".mobi", ".fb2", ".azw", ".azw3"}

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
class ResourceBook:
    filename: str          # e.g. "my-novel.pdf"
    collection: str        # parent collection slug
    size_bytes: int = 0
    ext: str = ""          # lowercase extension e.g. ".pdf"

    @property
    def display_name(self) -> str:
        return self.filename

    @property
    def is_image_render(self) -> bool:
        return self.ext in IMAGE_RENDER_FORMATS

    @property
    def is_text_render(self) -> bool:
        return self.ext in TEXT_RENDER_FORMATS

    @property
    def format_icon(self) -> str:
        icons = {".pdf": "📄", ".epub": "📗", ".mobi": "📘", ".cbz": "🗂️",
                 ".fb2": "📙", ".xps": "📋", ".azw": "📘", ".azw3": "📘"}
        return icons.get(self.ext, "📁")


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

    # ------------------------------------------------------------------ #
    # Resource Books (binary files: PDF, EPUB, MOBI, CBZ, ...)
    # ------------------------------------------------------------------ #

    def _resources_dir(self, coll: str) -> Path:
        d = self._coll_dir(coll) / "resources"
        d.mkdir(parents=True, exist_ok=True)
        return d

    def _resource_path(self, coll: str, filename: str) -> Path:
        return self._resources_dir(coll) / filename

    def list_resources(self, coll: str) -> list[ResourceBook]:
        """Return all imported resource files for a collection."""
        rdir = self._resources_dir(coll)
        out = []
        for f in sorted(rdir.iterdir()):
            if f.is_file() and f.suffix.lower() in RESOURCE_EXTENSIONS:
                out.append(ResourceBook(
                    filename=f.name,
                    collection=coll,
                    size_bytes=f.stat().st_size,
                    ext=f.suffix.lower(),
                ))
        return out

    def save_resource(self, coll: str, filename: str, data: bytes) -> bool:
        """Save uploaded binary file to the resources directory."""
        if not self._meta_path(coll).exists():
            return False
        ext = Path(filename).suffix.lower()
        if ext not in RESOURCE_EXTENSIONS:
            return False
        path = self._resource_path(coll, filename)
        path.write_bytes(data)
        return True

    def delete_resource(self, coll: str, filename: str) -> bool:
        """Delete a resource file."""
        path = self._resource_path(coll, filename)
        if not path.exists():
            return False
        path.unlink()
        return True

    def resource_page_count(self, coll: str, filename: str) -> int:
        """Return total page / chapter count for a resource."""
        try:
            import fitz  # PyMuPDF
            path = self._resource_path(coll, filename)
            if not path.exists():
                return 0
            doc = fitz.open(str(path))
            count = doc.page_count
            doc.close()
            return count
        except Exception:
            return 0

    def resource_page_image(self, coll: str, filename: str, page_n: int) -> bytes | None:
        """Render a page of a PDF/CBZ/XPS as PNG bytes (for image-render formats)."""
        try:
            import fitz  # PyMuPDF
            path = self._resource_path(coll, filename)
            if not path.exists():
                return None
            doc = fitz.open(str(path))
            if page_n < 0 or page_n >= doc.page_count:
                doc.close()
                return None
            page = doc.load_page(page_n)
            # 2x resolution for sharp rendering
            mat = fitz.Matrix(2, 2)
            pix = page.get_pixmap(matrix=mat)
            png_bytes = pix.tobytes("png")
            doc.close()
            return png_bytes
        except Exception:
            return None

    def resource_text_chapters(self, coll: str, filename: str) -> list[dict]:
        """Extract chapters/sections from EPUB/MOBI/FB2 for text-render formats.
        Returns list of dicts: [{title, html, index}]
        """
        try:
            import fitz  # PyMuPDF
            path = self._resource_path(coll, filename)
            if not path.exists():
                return []
            doc = fitz.open(str(path))
            toc = doc.get_toc()  # [[level, title, page], ...]
            chapters = []
            if toc:
                # Group pages by TOC entries
                for i, entry in enumerate(toc):
                    level, title, start_page = entry
                    end_page = toc[i + 1][2] if i + 1 < len(toc) else doc.page_count
                    html_parts = []
                    for p in range(start_page - 1, min(end_page, doc.page_count)):
                        page = doc.load_page(p)
                        html_parts.append(page.get_text("html"))
                    chapters.append({
                        "index": i,
                        "title": title,
                        "html": "".join(html_parts),
                    })
            else:
                # No TOC — treat entire doc as one chapter per page
                for p in range(doc.page_count):
                    page = doc.load_page(p)
                    chapters.append({
                        "index": p,
                        "title": f"Page {p + 1}",
                        "html": page.get_text("html"),
                    })
            doc.close()
            return chapters
        except Exception:
            return []
