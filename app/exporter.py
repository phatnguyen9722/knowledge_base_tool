"""Static HTML site exporter.

Renders every published post to a self-contained static site under an output
directory (default `dist/site/`): an `index.html` feed plus one `<slug>.html`
per post, with `style.css` copied alongside. Links are relative so the output
can be opened from disk or served by any static host.

This is intentionally independent of the FastAPI app/templates (which use
absolute routes + a request object); a small inline template keeps export
portable.
"""

from __future__ import annotations

import html
import shutil
from pathlib import Path

import mistune

from .config import load_settings
from .post_manager import PostManager

_md = mistune.create_markdown(
    escape=False, plugins=["strikethrough", "table", "url", "task_lists"]
)

_PAGE = """<!DOCTYPE html>
<html lang="en"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title><link rel="stylesheet" href="{css}">
</head><body><div class="layout"><main class="content">
{body}
</main></div></body></html>
"""


def _render_index(posts: list) -> str:
    items = []
    for p in posts:
        tags = " ".join(f'<span class="tag">#{html.escape(t)}</span>' for t in p.tags)
        items.append(
            f'<li class="card">'
            f'<div class="card-meta"><span class="cat">{html.escape(p.category)}</span>'
            f"<time>{p.updated}</time></div>"
            f'<h2 class="card-title"><a href="{p.slug}.html">{html.escape(p.title)}</a></h2>'
            f'<p class="summary">{html.escape(p.summary)}</p>'
            f'<div class="card-tags">{tags}</div></li>'
        )
    body = f'<h1>Knowledge Base</h1><ul class="feed">{"".join(items)}</ul>'
    return _PAGE.format(title="Knowledge Base", css="style.css", body=body)


def _render_post(post) -> str:
    tags = " ".join(f'<span class="tag">#{html.escape(t)}</span>' for t in post.tags)
    body = (
        '<article class="post"><a class="back" href="index.html">← Back</a>'
        f'<header class="post-head"><h1>{html.escape(post.title)}</h1>'
        f'<div class="post-meta"><span class="cat">{html.escape(post.category)}</span>'
        f'<span class="muted">created {post.created} · updated {post.updated}</span></div>'
        f'<div class="card-tags">{tags}</div></header>'
        f'<div class="markdown">{_md(post.content or "")}</div></article>'
    )
    return _PAGE.format(title=post.title, css="style.css", body=body)


def export_site(
    out_dir: Path | str = "dist/site",
    status: str | None = "published",
) -> dict:
    """Export the site. Returns {"out_dir", "count"}."""
    settings = load_settings()
    pm = PostManager(settings.posts_dir, settings.db_path)
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)

    posts = pm.list(status=status)
    (out / "index.html").write_text(_render_index(posts), encoding="utf-8")
    for post in posts:
        (out / f"{post.slug}.html").write_text(_render_post(post), encoding="utf-8")

    css = settings.static / "style.css"
    if css.exists():
        shutil.copyfile(css, out / "style.css")

    return {"out_dir": str(out), "count": len(posts)}
