"""TOEIC practice sets — parser and manager.

TOEIC files live in their own directory (``toeic/``), separate from ``posts/``.
Each file is markdown with YAML frontmatter plus a simple block format for
passages and questions:

    ---
    title: "Part 5 — Grammar Set 1"
    part: 5
    created: 2026-06-28
    ---

    ::: passage
    (Optional) reading passage in **markdown** — used for Part 6 / 7.
    :::

    ::: question
    The committee will _____ the proposal at the next meeting.
    - A. review
    - B. reviews
    - C. reviewing
    - D. reviewed
    answer: A
    note: After the modal **will**, use the base form *review*.
    :::

The body is rendered into structured `ToeicQuestion` objects so the UI can show
radio-button choices and reveal the correct answer + note on demand.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

import frontmatter
import mistune
from slugify import slugify

__all__ = [
    "ToeicQuestion", "ToeicSet", "ToeicManager", "parse_toeic",
    "Photograph", "QRPair", "ListeningQuestion", "ListeningGroup",
    "ListeningSet", "parse_listening",
]

_md = mistune.create_markdown(
    escape=False, hard_wrap=True, plugins=["strikethrough", "table", "url", "task_lists"]
)

_OPEN_RE = re.compile(r"^:::\s*(question|passage)\b", re.IGNORECASE)
_CLOSE_RE = re.compile(r"^:::\s*$")
_CHOICE_RE = re.compile(r"^\s*-?\s*([A-Da-d])[.)]\s+(.*\S)\s*$")
_ANSWER_RE = re.compile(r"^\s*answer\s*:\s*([A-Da-d])\b", re.IGNORECASE)
_NOTE_RE = re.compile(r"^\s*note\s*:\s*(.*)$", re.IGNORECASE)


@dataclass
class ToeicQuestion:
    prompt: str
    choices: list[dict]          # [{"letter": "A", "text": "..."}]
    answer: str                  # correct letter, e.g. "B"
    note_html: str = ""          # rendered markdown explanation


@dataclass
class ToeicSet:
    slug: str
    title: str
    part: int = 0
    created: str = ""
    updated: str = ""
    summary: str = ""
    tags: list[str] = field(default_factory=list)
    passage_html: str = ""
    questions: list[ToeicQuestion] = field(default_factory=list)


def _parse_question_block(buf: list[str]) -> ToeicQuestion:
    prompt: list[str] = []
    choices: list[dict] = []
    answer = ""
    note: list[str] = []
    mode = "prompt"
    for ln in buf:
        m_ans = _ANSWER_RE.match(ln)
        if m_ans:
            answer = m_ans.group(1).upper()
            mode = "post"
            continue
        m_note = _NOTE_RE.match(ln)
        if m_note:
            note.append(m_note.group(1))
            mode = "note"
            continue
        m_choice = _CHOICE_RE.match(ln)
        if m_choice and mode in ("prompt", "choice"):
            choices.append({"letter": m_choice.group(1).upper(), "text": m_choice.group(2)})
            mode = "choice"
            continue
        if mode == "note":
            note.append(ln)
        elif mode == "prompt":
            prompt.append(ln)
        # lines after the answer that aren't a note are ignored
    return ToeicQuestion(
        prompt="\n".join(prompt).strip(),
        choices=choices,
        answer=answer,
        note_html=_md("\n".join(note).strip()) if note else "",
    )


def parse_toeic(text: str, slug: str) -> ToeicSet:
    """Parse a TOEIC markdown file's text into a ToeicSet."""
    fm = frontmatter.loads(text)
    meta = fm.metadata or {}

    passages: list[str] = []
    questions: list[ToeicQuestion] = []
    lines = fm.content.splitlines()
    i, n = 0, len(lines)
    while i < n:
        m = _OPEN_RE.match(lines[i].strip())
        if m:
            kind = m.group(1).lower()
            i += 1
            buf: list[str] = []
            while i < n and not _CLOSE_RE.match(lines[i].strip()):
                buf.append(lines[i])
                i += 1
            i += 1  # skip the closing :::
            if kind == "passage":
                passages.append("\n".join(buf).strip())
            else:
                questions.append(_parse_question_block(buf))
        else:
            i += 1

    try:
        part = int(meta.get("part", 0) or 0)
    except (ValueError, TypeError):
        part = 0

    return ToeicSet(
        slug=slug,
        title=str(meta.get("title", slug)),
        part=part,
        created=str(meta.get("created", "")),
        updated=str(meta.get("updated", "")),
        summary=str(meta.get("summary", "")),
        tags=[str(t).lower().strip() for t in (meta.get("tags") or [])],
        passage_html=_md("\n\n".join(passages)) if passages else "",
        questions=questions,
    )


# ---------------------------------------------------------------------------
# Listening (Parts 1-4) — dataclasses
# ---------------------------------------------------------------------------

@dataclass
class Photograph:
    """Part 1 item — a photo the test-taker looks at while hearing 4 statements."""
    image_url: str = ""
    audio_url: str = ""
    choices: list[dict] = field(default_factory=list)   # A-D
    answer: str = ""
    note_html: str = ""


@dataclass
class QRPair:
    """Part 2 item — a question/statement + 3 responses."""
    audio_url: str = ""
    transcript: str = ""      # written text of the question / statement
    choices: list[dict] = field(default_factory=list)   # A-C
    answer: str = ""
    note_html: str = ""


@dataclass
class ListeningQuestion:
    """Sub-question inside a Part 3 or 4 group."""
    prompt: str = ""
    choices: list[dict] = field(default_factory=list)
    answer: str = ""
    graphic_url: str = ""     # new format: optional reference graphic
    note_html: str = ""


@dataclass
class ListeningGroup:
    """Part 3 (conversation) or Part 4 (short talk) — one audio with 3-4 Qs."""
    audio_url: str = ""
    transcript: str = ""
    questions: list[ListeningQuestion] = field(default_factory=list)

    @property
    def question_count(self) -> int:
        return len(self.questions)


@dataclass
class ListeningSet:
    """A listening practice file (Parts 1-4)."""
    slug: str = ""
    title: str = ""
    part: int = 1
    format: str = "new"      # "old" | "new"  (pre-/post-2016 format)
    created: str = ""
    updated: str = ""
    summary: str = ""
    photographs: list[Photograph] = field(default_factory=list)
    qr_pairs: list[QRPair] = field(default_factory=list)
    groups: list[ListeningGroup] = field(default_factory=list)

    @property
    def item_count(self) -> int:
        return (len(self.photographs) + len(self.qr_pairs) +
                sum(g.question_count for g in self.groups))

    @property
    def group_count(self) -> int:
        return len(self.groups)


# ---------------------------------------------------------------------------
# Listening file format
# ---------------------------------------------------------------------------
# Top-level block types:
#   ::: photo     → Part 1 item
#   ::: qr        → Part 2 item
#   ::: group     → Part 3/4 conversation or talk
# Inside ::: group, nested sub-blocks:
#   ::: cq        → sub-question (closes with its own :::)
# ::: alone closes the current level.
#
# Field lines inside a block (before choices):
#   audio: /toeic-audio/filename.mp3
#   image: /img/filename.jpg         (photo only)
#   transcript: "single-line text"   (qr only, or use body of group)
#   graphic: /img/table.png          (cq only — new-format reference graphic)

_L1_OPEN = re.compile(r"^:::\s*(photo|qr|group)\b", re.IGNORECASE)
_L2_OPEN = re.compile(r"^:::\s*cq\b", re.IGNORECASE)
_CLOSE = re.compile(r"^:::\s*$")
_KV = re.compile(r"^(audio|image|transcript|graphic)\s*:\s*(.+)$", re.IGNORECASE)


def _parse_kv(line: str) -> tuple[str, str] | None:
    m = _KV.match(line.strip())
    return (m.group(1).lower(), m.group(2).strip()) if m else None


def _parse_cq_buf(buf: list[str]) -> ListeningQuestion:
    """Parse lines of a ::: cq block into a ListeningQuestion."""
    graphic_url = ""
    prompt: list[str] = []
    choices: list[dict] = []
    answer = ""
    note: list[str] = []
    mode = "prompt"
    for ln in buf:
        kv = _parse_kv(ln)
        if kv and kv[0] == "graphic" and mode == "prompt":
            graphic_url = kv[1]
            continue
        m_ans = _ANSWER_RE.match(ln)
        if m_ans:
            answer = m_ans.group(1).upper()
            mode = "post"
            continue
        m_note = _NOTE_RE.match(ln)
        if m_note:
            note.append(m_note.group(1))
            mode = "note"
            continue
        m_ch = _CHOICE_RE.match(ln)
        if m_ch and mode in ("prompt", "choice"):
            choices.append({"letter": m_ch.group(1).upper(), "text": m_ch.group(2)})
            mode = "choice"
            continue
        if mode == "note":
            note.append(ln)
        elif mode == "prompt":
            prompt.append(ln)
    return ListeningQuestion(
        prompt="\n".join(prompt).strip(),
        choices=choices,
        answer=answer,
        graphic_url=graphic_url,
        note_html=_md("\n".join(note).strip()) if note else "",
    )


def _parse_photo_buf(buf: list[str]) -> Photograph:
    image_url = audio_url = answer = ""
    choices: list[dict] = []
    note: list[str] = []
    mode = "meta"
    for ln in buf:
        kv = _parse_kv(ln)
        if kv and mode == "meta":
            if kv[0] == "image":
                image_url = kv[1]
            elif kv[0] == "audio":
                audio_url = kv[1]
            continue
        m_ans = _ANSWER_RE.match(ln)
        if m_ans:
            answer = m_ans.group(1).upper()
            mode = "post"
            continue
        m_note = _NOTE_RE.match(ln)
        if m_note:
            note.append(m_note.group(1))
            mode = "note"
            continue
        m_ch = _CHOICE_RE.match(ln)
        if m_ch and mode in ("meta", "choice"):
            choices.append({"letter": m_ch.group(1).upper(), "text": m_ch.group(2)})
            mode = "choice"
            continue
        if mode == "note":
            note.append(ln)
    return Photograph(
        image_url=image_url, audio_url=audio_url, choices=choices,
        answer=answer, note_html=_md("\n".join(note).strip()) if note else "",
    )


def _parse_qr_buf(buf: list[str]) -> QRPair:
    audio_url = transcript = answer = ""
    choices: list[dict] = []
    note: list[str] = []
    mode = "meta"
    for ln in buf:
        kv = _parse_kv(ln)
        if kv and mode == "meta":
            if kv[0] == "audio":
                audio_url = kv[1]
            elif kv[0] == "transcript":
                transcript = kv[1].strip('"\'')
            continue
        m_ans = _ANSWER_RE.match(ln)
        if m_ans:
            answer = m_ans.group(1).upper()
            mode = "post"
            continue
        m_note = _NOTE_RE.match(ln)
        if m_note:
            note.append(m_note.group(1))
            mode = "note"
            continue
        m_ch = _CHOICE_RE.match(ln)
        if m_ch and mode in ("meta", "choice"):
            choices.append({"letter": m_ch.group(1).upper(), "text": m_ch.group(2)})
            mode = "choice"
            continue
        if mode == "note":
            note.append(ln)
        elif mode == "meta" and ln.strip():
            # bare text after meta = transcript
            transcript = ln.strip().strip('"\'')
    return QRPair(
        audio_url=audio_url, transcript=transcript, choices=choices,
        answer=answer, note_html=_md("\n".join(note).strip()) if note else "",
    )


def _parse_group_buf(buf: list[str]) -> ListeningGroup:
    """Parse lines of a ::: group block (may contain nested ::: cq blocks)."""
    audio_url = ""
    transcript: list[str] = []
    questions: list[ListeningQuestion] = []

    i, n = 0, len(buf)
    while i < n:
        ln = buf[i]
        # Nested ::: cq opener
        if _L2_OPEN.match(ln.strip()):
            i += 1
            cq_buf: list[str] = []
            while i < n and not _CLOSE.match(buf[i].strip()):
                cq_buf.append(buf[i])
                i += 1
            i += 1  # skip closing :::
            questions.append(_parse_cq_buf(cq_buf))
            continue
        # Key-value metadata
        kv = _parse_kv(ln)
        if kv and kv[0] == "audio" and not transcript:
            audio_url = kv[1]
            i += 1
            continue
        # Everything else is the transcript body
        transcript.append(ln)
        i += 1

    return ListeningGroup(
        audio_url=audio_url,
        transcript="\n".join(transcript).strip(),
        questions=questions,
    )


def parse_listening(text: str, slug: str) -> ListeningSet:
    """Parse a TOEIC listening markdown file into a ListeningSet."""
    fm = frontmatter.loads(text)
    meta = fm.metadata or {}

    photographs: list[Photograph] = []
    qr_pairs: list[QRPair] = []
    groups: list[ListeningGroup] = []

    lines = fm.content.splitlines()
    i, n = 0, len(lines)
    while i < n:
        m = _L1_OPEN.match(lines[i].strip())
        if m:
            kind = m.group(1).lower()
            i += 1
            buf: list[str] = []
            depth = 1
            while i < n and depth > 0:
                if _L1_OPEN.match(lines[i].strip()) or _L2_OPEN.match(lines[i].strip()):
                    depth += 1
                elif _CLOSE.match(lines[i].strip()):
                    depth -= 1
                    if depth == 0:
                        i += 1
                        break
                if depth > 0:
                    buf.append(lines[i])
                i += 1
            if kind == "photo":
                photographs.append(_parse_photo_buf(buf))
            elif kind == "qr":
                qr_pairs.append(_parse_qr_buf(buf))
            elif kind == "group":
                groups.append(_parse_group_buf(buf))
        else:
            i += 1

    try:
        part = int(meta.get("part", 1) or 1)
    except (ValueError, TypeError):
        part = 1
    fmt = str(meta.get("format", "new")).lower()
    if fmt not in ("old", "new"):
        fmt = "new"

    return ListeningSet(
        slug=slug,
        title=str(meta.get("title", slug)),
        part=part,
        format=fmt,
        created=str(meta.get("created", "")),
        updated=str(meta.get("updated", "")),
        summary=str(meta.get("summary", "")),
        photographs=photographs,
        qr_pairs=qr_pairs,
        groups=groups,
    )


class ToeicManager:
    def __init__(self, toeic_dir: Path):
        self.toeic_dir = Path(toeic_dir)
        self.toeic_dir.mkdir(parents=True, exist_ok=True)

    def _path(self, slug: str) -> Path:
        return self.toeic_dir / f"{slug}.md"

    def _unique_slug(self, title: str) -> str:
        base = slugify(title, allow_unicode=True) or "toeic"
        slug, n = base, 2
        while self._path(slug).exists():
            slug = f"{base}-{n}"
            n += 1
        return slug

    def create(self, data: dict) -> str:
        """Write a new TOEIC set file (frontmatter + raw block body). Returns slug."""
        slug = self._unique_slug(data.get("title", ""))
        today = date.today().isoformat()
        meta = {
            "title": data.get("title", "").strip() or slug,
            "part": int(data.get("part", 0) or 0),
            "created": data.get("created", today),
            "updated": today,
            "summary": data.get("summary", "").strip(),
            "tags": [str(t).lower().strip() for t in (data.get("tags") or []) if str(t).strip()],
        }
        fm = frontmatter.Post(data.get("content", ""), **meta)
        self.toeic_dir.mkdir(parents=True, exist_ok=True)
        self._path(slug).write_text(frontmatter.dumps(fm), encoding="utf-8")
        return slug

    def read(self, slug: str) -> ToeicSet | None:
        path = self._path(slug)
        if not path.exists():
            return None
        return parse_toeic(path.read_text(encoding="utf-8"), slug)

    def list(self) -> list[ToeicSet]:
        """All reading sets (Parts 5-7), sorted by part then title."""
        sets = []
        for f in self.toeic_dir.glob("*.md"):
            if f.stem.lower() == "readme":
                continue
            raw = f.read_text(encoding="utf-8")
            fm = frontmatter.loads(raw)
            if str(fm.metadata.get("type", "")).lower() == "listening":
                continue   # skip listening files here
            s = self.read(f.stem)
            if s and s.questions:
                sets.append(s)
        sets.sort(key=lambda s: (s.part, s.title.lower()))
        return sets

    # ------------------------------------------------------------------ #
    # Listening (Parts 1-4)
    # ------------------------------------------------------------------ #
    def _l_path(self, slug: str) -> Path:
        return self.toeic_dir / f"l-{slug}.md"   # 'l-' prefix → avoids slug collision

    def _l_unique_slug(self, title: str) -> str:
        base = slugify(title, allow_unicode=True) or "listening"
        slug, n = base, 2
        while self._l_path(slug).exists():
            slug = f"{base}-{n}"
            n += 1
        return slug

    def create_listening(self, data: dict) -> str:
        """Create a new listening practice file. Returns slug."""
        slug = self._l_unique_slug(data.get("title", ""))
        today = date.today().isoformat()
        try:
            part = int(data.get("part", 1) or 1)
        except (ValueError, TypeError):
            part = 1
        fmt = data.get("format", "new")
        if fmt not in ("old", "new"):
            fmt = "new"
        meta = {
            "type": "listening",
            "title": data.get("title", "").strip() or slug,
            "part": part,
            "format": fmt,
            "created": today,
            "updated": today,
            "summary": data.get("summary", "").strip(),
        }
        fm = frontmatter.Post(data.get("content", ""), **meta)
        self.toeic_dir.mkdir(parents=True, exist_ok=True)
        self._l_path(slug).write_text(frontmatter.dumps(fm), encoding="utf-8")
        return slug

    def read_listening(self, slug: str) -> ListeningSet | None:
        path = self._l_path(slug)
        if not path.exists():
            return None
        return parse_listening(path.read_text(encoding="utf-8"), slug)

    def raw_listening(self, slug: str) -> str:
        path = self._l_path(slug)
        if not path.exists():
            return ""
        fm = frontmatter.load(str(path))
        return fm.content

    def list_listening(self) -> list[ListeningSet]:
        """All listening sets, sorted by part then format (new→old) then title."""
        out = []
        for f in self.toeic_dir.glob("l-*.md"):
            s = self.read_listening(f.stem[2:])   # strip 'l-' prefix
            if s:
                out.append(s)
        out.sort(key=lambda s: (s.part, s.format == "old", s.title.lower()))
        return out
