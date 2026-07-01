"""Markdown rendering with Table-of-Contents extraction.

`render_with_toc()` renders a post's body to HTML while (a) injecting a unique
`id` on every heading so it can be linked to, and (b) collecting a flat,
ordered list of TOC entries `{level, text, id}` for headings h1–h3.

A fresh renderer is built per call so the collected TOC is never shared across
concurrent requests.
"""

from __future__ import annotations

import re

import mistune
from slugify import slugify

_PLUGINS = ["strikethrough", "table", "url", "task_lists"]
_TAG_RE = re.compile(r"<[^>]+>")

# Headings up to this level appear in the TOC.
TOC_MAX_LEVEL = 3


def _strip_tags(s: str) -> str:
    return _TAG_RE.sub("", s).strip()


class _TocRenderer(mistune.HTMLRenderer):
    """HTML renderer that adds heading ids and records a TOC."""

    def __init__(self):
        super().__init__(escape=False)
        self.toc: list[dict] = []
        self._seen: dict[str, int] = {}

    def _anchor(self, label: str) -> str:
        base = slugify(label, allow_unicode=True) or "section"
        n = self._seen.get(base, 0)
        self._seen[base] = n + 1
        return base if n == 0 else f"{base}-{n + 1}"

    def heading(self, text: str, level: int, **attrs) -> str:
        label = _strip_tags(text)
        anchor = self._anchor(label)
        if level <= TOC_MAX_LEVEL and label:
            self.toc.append({"level": level, "text": label, "id": anchor})
        return f'<h{level} id="{anchor}">{text}</h{level}>\n'


def render_with_toc(text: str) -> tuple[str, list[dict]]:
    """Render markdown to (html, toc). `toc` is a list of {level, text, id}."""
    renderer = _TocRenderer()
    md = mistune.create_markdown(renderer=renderer, plugins=_PLUGINS)
    html = md(text or "")
    return html, renderer.toc
