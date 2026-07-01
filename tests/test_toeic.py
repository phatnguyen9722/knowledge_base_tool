"""Tests for the TOEIC practice feature (parser, manager, pages)."""

import pytest
from fastapi.testclient import TestClient

from app.toeic import ToeicManager, parse_toeic

SAMPLE = """\
---
title: "Part 5 — Set A"
part: 5
created: 2026-06-28
summary: "demo"
tags: [Grammar]
---

::: passage
A short **passage** for context.
:::

::: question
The team will _____ the report tomorrow.
- A. finish
- B. finishes
- C. finishing
- D. finished
answer: A
note: After **will** use the base form.
Second line of the note.
:::

::: question
She has lived here _____ 2010.
- A. for
- B. since
answer: B
note: Use *since* with a start point.
:::
"""


# --------------------------------------------------------------------------- #
# Parser
# --------------------------------------------------------------------------- #
def test_parse_basic_structure():
    s = parse_toeic(SAMPLE, "set-a")
    assert s.slug == "set-a"
    assert s.title == "Part 5 — Set A"
    assert s.part == 5
    assert s.tags == ["grammar"]
    assert "<strong>passage</strong>" in s.passage_html
    assert len(s.questions) == 2


def test_parse_question_fields():
    s = parse_toeic(SAMPLE, "set-a")
    q1 = s.questions[0]
    assert q1.prompt.startswith("The team will")
    assert [c["letter"] for c in q1.choices] == ["A", "B", "C", "D"]
    assert q1.choices[0]["text"] == "finish"
    assert q1.answer == "A"
    # multi-line note rendered as markdown
    assert "base form" in q1.note_html
    assert "Second line" in q1.note_html


def test_parse_handles_two_choice_question():
    s = parse_toeic(SAMPLE, "set-a")
    q2 = s.questions[1]
    assert len(q2.choices) == 2
    assert q2.answer == "B"


# --------------------------------------------------------------------------- #
# Manager (stored in toeic dir, not posts)
# --------------------------------------------------------------------------- #
def test_manager_list_and_read(tmp_path):
    tdir = tmp_path / "toeic"
    tdir.mkdir()
    (tdir / "set-a.md").write_text(SAMPLE, encoding="utf-8")
    (tdir / "README.md").write_text("# docs\n", encoding="utf-8")

    mgr = ToeicManager(tdir)
    sets = mgr.list()
    assert [s.slug for s in sets] == ["set-a"]  # README excluded
    assert mgr.read("set-a").part == 5
    assert mgr.read("missing") is None


def test_manager_sorts_by_part(tmp_path):
    tdir = tmp_path / "toeic"
    tdir.mkdir()
    (tdir / "p7.md").write_text(
        "---\ntitle: P7\npart: 7\n---\n::: question\nQ?\n- A. x\nanswer: A\n:::\n",
        encoding="utf-8")
    (tdir / "p5.md").write_text(
        "---\ntitle: P5\npart: 5\n---\n::: question\nQ?\n- A. x\nanswer: A\n:::\n",
        encoding="utf-8")
    mgr = ToeicManager(tdir)
    assert [s.part for s in mgr.list()] == [5, 7]


# --------------------------------------------------------------------------- #
# Routes
# --------------------------------------------------------------------------- #
@pytest.fixture
def client(tmp_path, monkeypatch):
    import app.main as m

    tdir = tmp_path / "toeic"
    tdir.mkdir()
    (tdir / "set-a.md").write_text(SAMPLE, encoding="utf-8")
    monkeypatch.setattr(m, "toeic", ToeicManager(tdir))
    with TestClient(m.app) as c:
        yield c


def test_toeic_button_in_topbar(client):
    assert 'href="/toeic"' in client.get("/").text


def test_toeic_index_lists_sets(client):
    html = client.get("/toeic").text
    assert "TOEIC Practice" in html
    assert "Part 5 — Set A" in html
    assert 'href="/toeic/set-a"' in html


def test_toeic_detail_renders_radios_and_hidden_answer(client):
    html = client.get("/toeic/set-a").text
    # radio buttons for choices
    assert 'type="radio"' in html
    assert 'name="q1"' in html and 'value="A"' in html
    # passage rendered
    assert "<strong>passage</strong>" in html
    # answer is present but in a hidden box behind a toggle
    assert 'data-answer-toggle' in html
    assert 'class="answer-box" hidden' in html
    assert "Correct answer: A" in html
    # correctness data attr for JS
    assert 'data-correct="A"' in html


def test_toeic_detail_404(client):
    assert client.get("/toeic/nope").status_code == 404


def test_app_js_has_toeic_logic():
    from pathlib import Path
    js = (Path("static") / "app.js").read_text(encoding="utf-8")
    assert "data-answer-toggle" in js
    assert "revealAnswer" in js
    assert "toeic-toggle-all" in js
