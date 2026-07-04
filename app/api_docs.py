"""API Documentation — store, parse, and display REST API reference.

Each project is one markdown file in ``api-docs/``.  Frontmatter holds the
project metadata (title, base_url, version, auth, tags).  The body contains:

  * Free-form markdown notes (before any ::: endpoint block).
  * One or more ``::: endpoint`` blocks, each describing a single API operation.

Endpoint block format
---------------------

    ::: endpoint
    method: POST
    path: /users
    title: Create User
    description: Creates a new user account.
    auth: Bearer token               (overrides project-level auth)

    param: name   | body    | string  | required | Full name of the user
    param: email  | body    | string  | required | Email address (unique)
    param: role   | body    | string  | optional | admin, member, or viewer

    response: 201 | Created
    {"id": 42, "name": "Jane Doe", "email": "jane@example.com"}

    response: 400 | Bad Request
    {"error": "email already exists"}
    :::

* ``param:``   pipe-separated → name | location | type | required | description
  - location: query, body, path, header
  - required: required / optional / yes / no
* ``response:`` status | description, followed by example text until the
  next ``response:`` or the closing ``:::``.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

import frontmatter
import mistune
from slugify import slugify

__all__ = ["ApiParam", "ApiResponse", "ApiEndpoint", "ApiProject", "ApiDocsManager"]

_md = mistune.create_markdown(
    escape=False, hard_wrap=True, plugins=["strikethrough", "table", "url", "task_lists"]
)

_ENDPOINT_OPEN = re.compile(r"^:::\s*endpoint\b", re.IGNORECASE)
_CLOSE = re.compile(r"^:::\s*$")
_KV = re.compile(r"^(\w+)\s*:\s*(.*)")
_PARAM = re.compile(r"^param\s*:", re.IGNORECASE)
_RESPONSE = re.compile(r"^response\s*:\s*(\d+)\s*\|?\s*(.*)", re.IGNORECASE)

# HTTP method → CSS class suffix (for colour coding)
METHOD_CLASS = {
    "GET": "get", "POST": "post", "PUT": "put",
    "DELETE": "delete", "PATCH": "patch",
    "HEAD": "head", "OPTIONS": "options",
}


@dataclass
class ApiParam:
    name: str
    location: str      # query | body | path | header
    type: str          # string | integer | boolean | array | object | number
    required: bool
    description: str
    default: str = ""


@dataclass
class ApiResponse:
    status: int
    description: str
    example: str = ""  # raw JSON / text shown verbatim


@dataclass
class ApiEndpoint:
    method: str
    path: str
    title: str = ""
    description: str = ""
    auth: str = ""
    params: list[ApiParam] = field(default_factory=list)
    responses: list[ApiResponse] = field(default_factory=list)

    @property
    def method_class(self) -> str:
        return METHOD_CLASS.get(self.method.upper(), "other")

    @property
    def param_groups(self) -> dict[str, list[ApiParam]]:
        """Params grouped by location for table display."""
        groups: dict[str, list[ApiParam]] = {}
        for p in self.params:
            groups.setdefault(p.location, []).append(p)
        return groups


@dataclass
class ApiProject:
    slug: str
    title: str
    base_url: str = ""
    version: str = ""
    description: str = ""
    auth: str = ""
    tags: list[str] = field(default_factory=list)
    notes_html: str = ""        # markdown body before any endpoint block
    endpoints: list[ApiEndpoint] = field(default_factory=list)
    created: str = ""
    updated: str = ""

    @property
    def endpoint_count(self) -> int:
        return len(self.endpoints)


# ---------------------------------------------------------------------------
# Parser
# ---------------------------------------------------------------------------

def _parse_param_line(line: str) -> ApiParam | None:
    """Parse `param: name | location | type | required | description`."""
    # strip the 'param:' prefix
    rest = re.sub(r"^param\s*:\s*", "", line, flags=re.IGNORECASE)
    parts = [p.strip() for p in rest.split("|")]
    if len(parts) < 2:
        return None
    name = parts[0]
    location = parts[1].lower() if len(parts) > 1 else "query"
    typ = parts[2] if len(parts) > 2 else "string"
    req_raw = parts[3].lower() if len(parts) > 3 else "optional"
    required = req_raw in ("required", "yes", "true", "1")
    desc = parts[4] if len(parts) > 4 else ""
    return ApiParam(name=name, location=location, type=typ,
                    required=required, description=desc)


def _parse_endpoint_buf(buf: list[str]) -> ApiEndpoint:
    """Parse the lines inside a ::: endpoint … ::: block."""
    meta: dict[str, str] = {}
    params: list[ApiParam] = []
    responses: list[ApiResponse] = []

    # First pass: collect key-value meta and params
    # Second pass: collect response examples (multi-line after a response: header)
    i, n = 0, len(buf)
    current_resp: ApiResponse | None = None
    resp_example_lines: list[str] = []

    def _flush_resp():
        nonlocal current_resp, resp_example_lines
        if current_resp is not None:
            current_resp.example = "\n".join(resp_example_lines).strip()
            responses.append(current_resp)
        current_resp = None
        resp_example_lines = []

    while i < n:
        line = buf[i]
        stripped = line.strip()

        # param: line
        if _PARAM.match(stripped):
            _flush_resp()
            p = _parse_param_line(stripped)
            if p:
                params.append(p)
            i += 1
            continue

        # response: <status> | <description>
        m_resp = _RESPONSE.match(stripped)
        if m_resp:
            _flush_resp()
            status = int(m_resp.group(1))
            desc = m_resp.group(2).strip()
            current_resp = ApiResponse(status=status, description=desc)
            i += 1
            continue

        # key: value metadata (only collected before first param/response)
        if current_resp is None and not params:
            m_kv = _KV.match(stripped)
            if m_kv:
                key = m_kv.group(1).lower()
                val = m_kv.group(2).strip()
                meta[key] = val
                i += 1
                continue

        # response example body
        if current_resp is not None:
            resp_example_lines.append(line)
            i += 1
            continue

        i += 1

    _flush_resp()

    method = meta.get("method", "GET").upper()
    return ApiEndpoint(
        method=method,
        path=meta.get("path", "/"),
        title=meta.get("title", ""),
        description=meta.get("description", ""),
        auth=meta.get("auth", ""),
        params=params,
        responses=responses,
    )


def parse_api_project(text: str, slug: str) -> ApiProject:
    """Parse an API project markdown file into an ApiProject."""
    fm = frontmatter.loads(text)
    meta = fm.metadata or {}

    notes_buf: list[str] = []
    endpoints: list[ApiEndpoint] = []

    lines = fm.content.splitlines()
    i, n = 0, len(lines)
    while i < n:
        if _ENDPOINT_OPEN.match(lines[i].strip()):
            i += 1
            buf: list[str] = []
            while i < n and not _CLOSE.match(lines[i].strip()):
                buf.append(lines[i])
                i += 1
            i += 1  # skip closing :::
            endpoints.append(_parse_endpoint_buf(buf))
        else:
            notes_buf.append(lines[i])
            i += 1

    # Notes = everything before the first endpoint block
    notes_text = "\n".join(notes_buf).strip()

    return ApiProject(
        slug=slug,
        title=str(meta.get("title", slug)),
        base_url=str(meta.get("base_url", "")),
        version=str(meta.get("version", "")),
        description=str(meta.get("description", "")),
        auth=str(meta.get("auth", "")),
        tags=[str(t).lower().strip() for t in (meta.get("tags") or [])],
        notes_html=_md(notes_text) if notes_text else "",
        endpoints=endpoints,
        created=str(meta.get("created", "")),
        updated=str(meta.get("updated", "")),
    )


# ---------------------------------------------------------------------------
# Manager
# ---------------------------------------------------------------------------

class ApiDocsManager:
    def __init__(self, docs_dir: Path):
        self.docs_dir = Path(docs_dir)
        self.docs_dir.mkdir(parents=True, exist_ok=True)

    def _path(self, slug: str) -> Path:
        return self.docs_dir / f"{slug}.md"

    def _unique_slug(self, title: str) -> str:
        base = slugify(title, allow_unicode=True) or "api"
        slug, n = base, 2
        while self._path(slug).exists():
            slug = f"{base}-{n}"
            n += 1
        return slug

    def create(self, data: dict) -> str:
        today = date.today().isoformat()
        slug = self._unique_slug(data.get("title", ""))
        meta = {
            "title": data.get("title", "").strip() or slug,
            "base_url": data.get("base_url", "").strip(),
            "version": data.get("version", "").strip(),
            "description": data.get("description", "").strip(),
            "auth": data.get("auth", "").strip(),
            "tags": [str(t).lower().strip() for t in (data.get("tags") or [])
                     if str(t).strip()],
            "created": today,
            "updated": today,
        }
        fm = frontmatter.Post(data.get("content", ""), **meta)
        self._path(slug).write_text(frontmatter.dumps(fm), encoding="utf-8")
        return slug

    def read(self, slug: str) -> ApiProject | None:
        path = self._path(slug)
        if not path.exists():
            return None
        return parse_api_project(path.read_text(encoding="utf-8"), slug)

    def raw_content(self, slug: str) -> str:
        path = self._path(slug)
        if not path.exists():
            return ""
        fm = frontmatter.load(str(path))
        return fm.content

    def update(self, slug: str, data: dict) -> str | None:
        proj = self.read(slug)
        if not proj:
            return None
        today = date.today().isoformat()
        meta = {
            "title": data.get("title", proj.title).strip(),
            "base_url": data.get("base_url", proj.base_url).strip(),
            "version": data.get("version", proj.version).strip(),
            "description": data.get("description", proj.description).strip(),
            "auth": data.get("auth", proj.auth).strip(),
            "tags": [str(t).lower().strip() for t in
                     (data.get("tags") or proj.tags) if str(t).strip()],
            "created": proj.created or today,
            "updated": today,
        }
        fm = frontmatter.Post(data.get("content", self.raw_content(slug)), **meta)
        self._path(slug).write_text(frontmatter.dumps(fm), encoding="utf-8")
        return slug

    def delete(self, slug: str) -> bool:
        path = self._path(slug)
        if not path.exists():
            return False
        path.unlink()
        return True

    def list(self) -> list[ApiProject]:
        out = []
        for f in self.docs_dir.glob("*.md"):
            try:
                p = self.read(f.stem)
                if p:
                    out.append(p)
            except Exception:
                # Skip malformed files (e.g. bad YAML frontmatter) silently.
                pass
        out.sort(key=lambda p: p.title.lower())
        return out
