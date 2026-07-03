"""Shared settings loader.

Resolves the application's base directory (handling the PyInstaller bundle case)
and reads `config.yaml`, with sensible defaults. Used by both the web app
(`app.main`) and the CLI (`cli.py`) so they agree on paths.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path

import yaml


def base_dir() -> Path:
    """Project root in dev, or the unpacked bundle dir under PyInstaller."""
    if getattr(sys, "frozen", False):
        return Path(sys._MEIPASS)  # type: ignore[attr-defined]
    return Path(__file__).parent.parent


@dataclass
class Settings:
    base: Path
    posts_dir: Path
    img_dir: Path
    toeic_dir: Path
    books_dir: Path
    music_dir: Path
    notes_dir: Path
    tasks_dir: Path
    api_docs_dir: Path
    bookmarks_dir: Path
    db_path: Path
    templates: Path
    static: Path
    page_size: int
    theme: str
    host: str
    port: int


def load_settings(base: Path | None = None) -> Settings:
    base = Path(base) if base else base_dir()
    cfg_path = base / "config.yaml"
    cfg = yaml.safe_load(cfg_path.read_text(encoding="utf-8")) if cfg_path.exists() else {}
    cfg = cfg or {}
    data = cfg.get("data", {})
    ui = cfg.get("ui", {})
    server = cfg.get("server", {})
    posts_dir = base / data.get("posts_dir", "posts")
    # Image uploads live in img/, a sibling of posts/ (overridable via config).
    img_dir = base / data["img_dir"] if data.get("img_dir") else posts_dir.parent / "img"
    # TOEIC practice files live in toeic/ (separate from posts/).
    toeic_dir = base / data.get("toeic_dir", "toeic")
    # Books/novels live in books/ (one subfolder per collection).
    books_dir = base / data.get("books_dir", "books")
    # Music: imported .mp3 files + their markdown metadata sidecars.
    music_dir = base / data.get("music_dir", "music")
    # Quick notes (Title / date / content) with pin-to-favorite.
    notes_dir = base / data.get("notes_dir", "notes")
    # Tasks with version history
    tasks_dir = base / data.get("tasks_dir", "tasks")
    api_docs_dir = base / data.get("api_docs_dir", "api-docs")
    bookmarks_dir = base / data.get("bookmarks_dir", "bookmarks")
    return Settings(
        base=base,
        posts_dir=posts_dir,
        img_dir=img_dir,
        toeic_dir=toeic_dir,
        books_dir=books_dir,
        music_dir=music_dir,
        notes_dir=notes_dir,
        tasks_dir=tasks_dir,
        api_docs_dir=api_docs_dir,
        bookmarks_dir=bookmarks_dir,
        db_path=base / data.get("db_path", ".kb/search.db"),
        templates=base / "templates",
        static=base / "static",
        page_size=int(ui.get("page_size", 20)),
        theme=ui.get("theme", "vodka"),
        host=server.get("host", "127.0.0.1"),
        port=int(server.get("port", 5000)),
    )
