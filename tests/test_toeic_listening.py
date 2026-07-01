"""Tests for TOEIC Listening Parts 1-4 (parser, manager, routes)."""

import io
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.toeic import (
    ToeicManager,
    parse_listening,
)

# ── Sample content ─────────────────────────────────────────────────────────

PART1_TEXT = """\
---
type: listening
title: "Part 1 Sample"
part: 1
format: new
---

::: photo
image: /img/office.jpg
audio: /toeic-audio/p1.mp3
- A. A woman is typing.
- B. A man is reading.
- C. Chairs are stacked.
- D. Books are on the floor.
answer: A
note: The woman is clearly **typing** on her laptop.
:::

::: photo
image:
audio:
- A. A truck is parked outside.
- B. Workers are painting a wall.
- C. Goods are arranged on shelves.
- D. A forklift is moving boxes.
answer: C
:::
"""

PART2_TEXT = """\
---
type: listening
title: "Part 2 Sample"
part: 2
format: new
---

::: qr
audio: /toeic-audio/p2.mp3
transcript: "Where is the conference room?"
- A. It's on the third floor.
- B. Yes, the conference starts soon.
- C. I attended last year's conference.
answer: A
note: "Where" needs a location → (A) provides it.
:::

::: qr
audio:
transcript: "When does the next train leave?"
- A. At platform four.
- B. In about fifteen minutes.
- C. The ticket costs twelve dollars.
answer: B
:::
"""

PART3_TEXT = """\
---
type: listening
title: "Part 3 Sample"
part: 3
format: new
---

::: group
audio: /toeic-audio/p3.mp3

Man: I'd like to return this jacket.
Woman: Do you have a receipt?
Man: Yes, here it is.

::: cq
Why is the man at the store?
- A. To buy a jacket
- B. To return a purchase
- C. To exchange a product
- D. To get a refund card
answer: B
note: "I'd like to return this jacket."
:::

::: cq
What does the man produce?
- A. His credit card
- B. His ID
- C. A receipt
- D. A gift card
answer: C
:::
:::
"""

PART4_TEXT = """\
---
type: listening
title: "Part 4 Sample"
part: 4
format: old
---

::: group
audio:

Good morning. The sale begins on Saturday at 8 AM.
Discounts up to 50 percent on clothing.

::: cq
When does the sale begin?
- A. Friday
- B. Saturday
- C. Sunday
- D. Monday
answer: B
:::

::: cq
What is discounted?
- A. Electronics
- B. Furniture
- C. Clothing
- D. Footwear only
answer: C
note: "Discounts on clothing."
:::
:::
"""


# ── Parser unit tests ───────────────────────────────────────────────────────

def test_parse_part1_photographs():
    s = parse_listening(PART1_TEXT, "s")
    assert s.part == 1 and s.format == "new"
    assert len(s.photographs) == 2
    ph = s.photographs[0]
    assert ph.image_url == "/img/office.jpg"
    assert ph.audio_url == "/toeic-audio/p1.mp3"
    assert len(ph.choices) == 4
    assert ph.answer == "A"
    assert "<strong>" in ph.note_html         # markdown rendered
    assert s.photographs[1].image_url == ""   # empty image field ok


def test_parse_part2_qr_pairs():
    s = parse_listening(PART2_TEXT, "s")
    assert s.part == 2 and len(s.qr_pairs) == 2
    qr = s.qr_pairs[0]
    assert qr.transcript == "Where is the conference room?"
    assert qr.audio_url == "/toeic-audio/p2.mp3"
    assert len(qr.choices) == 3
    assert qr.answer == "A"
    assert s.qr_pairs[1].answer == "B"


def test_parse_part3_groups_with_nested_cq():
    s = parse_listening(PART3_TEXT, "s")
    assert s.part == 3 and len(s.groups) == 1
    grp = s.groups[0]
    assert grp.audio_url == "/toeic-audio/p3.mp3"
    assert "I'd like to return" in grp.transcript
    assert len(grp.questions) == 2
    assert grp.questions[0].answer == "B"
    assert grp.questions[1].answer == "C"
    assert s.item_count == 2


def test_parse_part4_old_format():
    s = parse_listening(PART4_TEXT, "s")
    assert s.part == 4 and s.format == "old"
    assert len(s.groups) == 1
    grp = s.groups[0]
    assert "Saturday" in grp.transcript
    assert grp.questions[0].answer == "B"
    assert grp.questions[1].answer == "C"
    assert "Discounts on clothing." in grp.questions[1].note_html


def test_invalid_format_defaults_to_new():
    text = "---\ntitle: x\npart: 1\nformat: bogus\n---\n"
    s = parse_listening(text, "x")
    assert s.format == "new"


# ── ToeicManager ────────────────────────────────────────────────────────────

@pytest.fixture
def mgr(tmp_path):
    return ToeicManager(tmp_path / "toeic")


def test_create_and_read_listening(mgr):
    slug = mgr.create_listening({
        "title": "Part 2 Test", "part": 2, "format": "old",
        "summary": "test",
        "content": PART2_TEXT.split("---")[-1],
    })
    assert (mgr.toeic_dir / f"l-{slug}.md").exists()
    s = mgr.read_listening(slug)
    assert s.part == 2 and s.format == "old"


def test_list_listening_separate_from_reading(mgr, tmp_path):
    # add a reading set (no type: listening)
    mgr.create({"title": "Part 5", "part": 5, "content":
                 "::: question\nX?\n- A. a\nanswer: A\n:::\n"})
    mgr.create_listening({"title": "Part 1 L", "part": 1, "content": ""})
    assert len(mgr.list()) >= 1              # reading
    assert len(mgr.list_listening()) == 1   # listening only
    assert mgr.list_listening()[0].part == 1


def test_list_listening_sorted_by_part(mgr):
    mgr.create_listening({"title": "P4", "part": 4, "content": ""})
    mgr.create_listening({"title": "P1", "part": 1, "content": ""})
    mgr.create_listening({"title": "P2", "part": 2, "content": ""})
    parts = [s.part for s in mgr.list_listening()]
    assert parts == [1, 2, 4]


# ── Routes ──────────────────────────────────────────────────────────────────

@pytest.fixture
def client(tmp_path, monkeypatch):
    import app.main as m
    from app.post_manager import PostManager
    from app.tag_manager import TagManager

    pm = PostManager(tmp_path / "posts", tmp_path / ".kb" / "search.db")
    tmgr = ToeicManager(tmp_path / "toeic")
    monkeypatch.setattr(m, "pm", pm)
    monkeypatch.setattr(m, "tm", TagManager(tmp_path / "posts"))
    monkeypatch.setattr(m, "toeic", tmgr)
    monkeypatch.setattr(m, "TOEIC_AUDIO_DIR", tmp_path / "toeic" / "audio")
    with TestClient(m.app) as c:
        c.toeic = tmgr
        yield c
    pm.search.close()


def test_listening_index_empty(client):
    assert client.get("/toeic/listening").status_code == 200
    assert "No listening sets" in client.get("/toeic/listening").text


def test_listening_new_form_per_part(client):
    for p in (1, 2, 3, 4):
        r = client.get(f"/toeic/listening/new?part={p}")
        assert r.status_code == 200
        assert "name=\"part\"" in r.text


def test_listening_create_and_detail(client):
    r = client.post("/toeic/listening/new", data={
        "title": "P1 Test", "part": "1", "format": "new",
        "summary": "x", "content": PART1_TEXT.split("---")[-1],
    }, follow_redirects=False)
    assert r.status_code == 303
    slug = r.headers["location"].split("/")[-1]

    det = client.get(f"/toeic/listening/{slug}").text
    assert "Part 1" in det
    assert "NEW FORMAT" in det
    assert 'type="radio"' in det            # choices rendered
    assert 'data-answer-toggle' in det      # show/hide button


def test_listening_detail_part3_shows_transcript(client):
    client.post("/toeic/listening/new", data={
        "title": "P3", "part": "3", "format": "new",
        "content": PART3_TEXT.split("---")[-1],
    }, follow_redirects=False)
    det = client.get("/toeic/listening/p3").text
    assert "Transcript" in det
    assert "I&#x27;d like to return" in det or "I'd like to return" in det


def test_listening_404(client):
    assert client.get("/toeic/listening/nope").status_code == 404


def test_audio_upload_endpoint(client, tmp_path, monkeypatch):
    import app.main as m
    adir = tmp_path / "toeic" / "audio"
    adir.mkdir(parents=True)
    monkeypatch.setattr(m, "TOEIC_AUDIO_DIR", adir)
    fake_mp3 = b"ID3\x03\x00\x00\x00\x00\x00\x21x\xff\xfb\x90\x00"
    r = client.post("/api/upload-audio",
                    files={"file": ("q1.mp3", io.BytesIO(fake_mp3), "audio/mpeg")})
    assert r.status_code == 200
    data = r.json()
    assert data["url"].startswith("/toeic-audio/")
    assert data["url"].endswith(".mp3")


def test_seeded_files_parse():
    """Verify every seeded listening file in toeic/ parses without error."""
    toeic_dir = Path("toeic")
    for f in toeic_dir.glob("l-*.md"):
        s = parse_listening(f.read_text(encoding="utf-8"), f.stem[2:])
        assert s.title
        assert s.part in (1, 2, 3, 4)
