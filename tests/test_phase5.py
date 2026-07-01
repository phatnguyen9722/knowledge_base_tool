"""Phase 5 tests: plugin hooks, static exporter, Typer CLI.

The tray launcher and PyInstaller bundle are not exercised here (they need a
display / a full build); see the Phase 5 report for manual verification steps.
"""

from pathlib import Path

import pytest
from typer.testing import CliRunner

from app import hooks
from app.config import Settings


def _settings(tmp_path) -> Settings:
    return Settings(
        base=tmp_path,
        posts_dir=tmp_path / "posts",
        img_dir=tmp_path / "img",
        toeic_dir=tmp_path / "toeic",
        books_dir=tmp_path / "books",
        music_dir=tmp_path / "music",
        notes_dir=tmp_path / "notes",
        api_docs_dir=tmp_path / "api-docs",
        bookmarks_dir=tmp_path / "bookmarks",
        db_path=tmp_path / ".kb" / "search.db",
        templates=Path("templates").resolve(),
        static=Path("static").resolve(),
        page_size=20,
        theme="light",
        host="127.0.0.1",
        port=5000,
    )


# --------------------------------------------------------------------------- #
# Hooks
# --------------------------------------------------------------------------- #
def test_hooks_fire_in_order(tmp_path):
    from app.post_manager import PostManager

    hooks.clear()
    events = []
    hooks.on("on_post_created")(lambda p: events.append(("c", p.slug)))
    hooks.on("on_post_updated")(lambda p: events.append(("u", p.slug)))
    hooks.on("on_post_deleted")(lambda slug: events.append(("d", slug)))

    pm = PostManager(tmp_path / "posts", tmp_path / ".kb" / "search.db")
    post = pm.create({"title": "Hi", "tags": ["a"], "category": "G", "status": "draft"})
    pm.update(post.slug, {"title": "Hi 2"})
    pm.delete(post.slug)
    pm.search.close()
    hooks.clear()

    assert events == [("c", post.slug), ("u", post.slug), ("d", post.slug)]


def test_on_unknown_event_raises():
    with pytest.raises(ValueError):
        hooks.on("nope")


def test_emit_isolates_handler_errors():
    hooks.clear()

    def boom(_):
        raise RuntimeError("plugin blew up")

    hooks.on("on_post_created")(boom)
    hooks.emit("on_post_created", None)  # must not raise
    hooks.clear()


# --------------------------------------------------------------------------- #
# Exporter
# --------------------------------------------------------------------------- #
def test_export_site_published_only(tmp_path, monkeypatch):
    import app.exporter as ex
    from app.post_manager import PostManager

    settings = _settings(tmp_path)
    monkeypatch.setattr(ex, "load_settings", lambda: settings)

    pm = PostManager(settings.posts_dir, settings.db_path)
    pm.create({"title": "Exported Post", "tags": ["docker"], "category": "DevOps",
               "status": "published", "content": "# Hi\n\n**bold**"})
    pm.create({"title": "Draft One", "tags": [], "category": "G", "status": "draft"})
    pm.search.close()

    out = tmp_path / "site"
    res = ex.export_site(out_dir=out)

    assert res["count"] == 1  # drafts excluded
    assert (out / "index.html").exists()
    assert (out / "exported-post.html").exists()
    assert not (out / "draft-one.html").exists()

    html = (out / "exported-post.html").read_text(encoding="utf-8")
    assert "<strong>bold</strong>" in html
    assert "<h1>Hi</h1>" in html
    assert (out / "style.css").exists()  # copied from static/

    index = (out / "index.html").read_text(encoding="utf-8")
    assert 'href="exported-post.html"' in index


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #
def test_cli_round_trip(tmp_path, monkeypatch):
    import cli as climod
    import app.exporter as ex

    settings = _settings(tmp_path)
    monkeypatch.setattr(climod, "load_settings", lambda *a, **k: settings)
    monkeypatch.setattr(ex, "load_settings", lambda: settings)

    runner = CliRunner()

    r = runner.invoke(climod.cli, ["new", "CLI Post", "--tags", "docker,ops",
                                   "--cat", "DevOps", "--status", "published"])
    assert r.exit_code == 0, r.output
    assert "Created" in r.output

    r = runner.invoke(climod.cli, ["list", "--status", "published"])
    assert r.exit_code == 0
    assert "CLI Post" in r.output

    r = runner.invoke(climod.cli, ["search", "CLI"])
    assert r.exit_code == 0
    assert "cli-post" in r.output

    r = runner.invoke(climod.cli, ["build-index"])
    assert r.exit_code == 0
    assert "Re-indexed" in r.output

    r = runner.invoke(climod.cli, ["export", "--out", str(tmp_path / "site")])
    assert r.exit_code == 0
    assert "Exported 1 post" in r.output
