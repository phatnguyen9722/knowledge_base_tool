"""Knowledge Base CLI (Typer).

Commands: new / list / search / serve / build-index / export.
Paths come from `config.yaml` via `app.config`, so the CLI and web app agree.
"""

from __future__ import annotations

from datetime import date

import typer

from app.config import load_settings

cli = typer.Typer(help="Knowledge Base CLI", no_args_is_help=True)


def _pm():
    from app.post_manager import PostManager

    s = load_settings()
    return PostManager(s.posts_dir, s.db_path)


@cli.command()
def new(
    title: str = typer.Argument(..., help="Post title"),
    category: str = typer.Option("General", "--cat", help="Category"),
    tags: str = typer.Option("", "--tags", help="Comma-separated tags"),
    status: str = typer.Option("draft", "--status", help="published|draft|archived"),
    series: str = typer.Option("", "--series", help="Series name"),
    order: int = typer.Option(0, "--order", help="Position within the series"),
):
    """Create a new post (status defaults to draft)."""
    pm = _pm()
    post = pm.create(
        {
            "title": title,
            "tags": [t.strip() for t in tags.split(",") if t.strip()],
            "category": category,
            "status": status,
            "series": series,
            "series_order": order,
            "created": date.today(),
            "updated": date.today(),
        }
    )
    typer.echo(f"Created: {pm._path(post.slug)}")


@cli.command(name="list")
def list_posts(status: str = typer.Option("published", "--status")):
    """List posts (pinned first, newest updated)."""
    pm = _pm()
    posts = pm.list(status=status or None)
    if not posts:
        typer.echo("(no posts)")
        return
    for p in posts:
        pin = "📌 " if p.pinned else "   "
        typer.echo(f"{pin}[{p.status.value}] {p.slug}  –  {p.title}")


@cli.command()
def search(
    query: str,
    tag: str = typer.Option("", "--tag"),
    category: str = typer.Option("", "--cat"),
):
    """Full-text search across posts."""
    pm = _pm()
    slugs = pm.search.search(query, tag=tag or None, category=category or None)
    if not slugs:
        typer.echo("(no matches)")
        return
    for s in slugs:
        post = pm.read(s)
        if post:
            typer.echo(f"{post.slug}  –  {post.title}")


@cli.command()
def serve(
    port: int = typer.Option(None, "--port", help="Override config port"),
    reload: bool = typer.Option(False, "--reload"),
):
    """Run the web app (Uvicorn)."""
    import uvicorn

    s = load_settings()
    uvicorn.run("app.main:app", host=s.host, port=port or s.port, reload=reload)


@cli.command(name="build-index")
def build_index():
    """Rebuild the tag index and the FTS5 search index from disk."""
    from app.tag_manager import TagManager

    pm = _pm()
    n = pm.rebuild_index()
    tags = TagManager(pm.posts_dir).rebuild()
    typer.echo(f"Re-indexed {n} post(s); {len(tags)} tag(s).")


@cli.command()
def export(
    out: str = typer.Option("dist/site", "--out", help="Output directory"),
    status: str = typer.Option("published", "--status"),
):
    """Export a static HTML site."""
    from app.exporter import export_site

    result = export_site(out_dir=out, status=status or None)
    typer.echo(f"Exported {result['count']} post(s) → {result['out_dir']}")


if __name__ == "__main__":
    cli()
