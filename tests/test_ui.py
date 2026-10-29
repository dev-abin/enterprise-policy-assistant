"""UI event routing tests; no model calls and no simulated human claims."""

from pathlib import Path
from types import SimpleNamespace
from typing import ClassVar

import pytest
from streamlit.testing.v1 import AppTest

from policy_qa import ui

SOURCE = {
    "chunk_id": "expenses/travel-deadline",
    "document_id": "expenses",
    "section_id": "travel-deadline",
    "text": "Travel expense claims\nSubmit claims within 30 calendar days.",
}


class FakeRun:
    calls: ClassVar[list[tuple]] = []

    def __init__(self, *args):
        self.pending = None
        self.state = {}
        self.failed = False
        self.trace = SimpleNamespace(events=[])

    def start(self, text):
        self.calls.append(("start", text))
        self.pending = {"question": "Which claim?", "options": ["Travel", "Medical"]}

    def resume(self, text="", cancel=False):
        self.calls.append(("resume", text, cancel))
        self.pending = None
        self.state = {
            "final": {
                "answer": "Cancelled" if cancel else "30 calendar days",
                "source_ids": [] if cancel else [SOURCE["chunk_id"]],
            },
            "evidence": [] if cancel else [SOURCE],
        }


def app(monkeypatch):
    FakeRun.calls = []
    monkeypatch.setattr(ui, "Run", FakeRun)
    monkeypatch.setattr(ui, "PolicyIndex", lambda: object())
    monkeypatch.setattr(ui, "Ollama", lambda: object())
    return AppTest.from_file(
        Path(__file__).resolve().parents[1] / "app.py", default_timeout=15
    ).run()


def test_ui_clarification_resume_and_rerender(monkeypatch):
    at = app(monkeypatch)
    at.chat_input[0].set_value("When should I claim?").run()
    assert not at.exception
    assert FakeRun.calls == [("start", "When should I claim?")]
    at.run()
    assert len(FakeRun.calls) == 1
    at.chat_input[0].set_value("Travel").run()
    assert FakeRun.calls[-1] == ("resume", "Travel", False)
    assert not at.chat_input[0].disabled
    assert not at.expander
    assert not at.json
    answer = next(m.value for m in at.markdown if "30 calendar days <abbr" in m.value)
    assert 'title="expenses.txt · Travel expense claims"' in answer
    assert ">[1]</abbr>" in answer
    assert not any("Travel expense claims" in c.value for c in at.caption)
    assert len(at.chat_message[-1].markdown) == 1
    assert not at.chat_message[-1].caption
    assert not at.exception
    at.run()
    assert len(FakeRun.calls) == 2
    previous_run = at.session_state["run"]
    at.chat_input[0].set_value("Who approves system access?").run()
    assert FakeRun.calls[-1] == ("start", "Who approves system access?")
    assert at.session_state["run"] is not previous_run
    assert any(
        message["text"] == "30 calendar days"
        for message in at.session_state["messages"]
    )
    assert not at.sidebar.button
    assert not at.exception


@pytest.mark.parametrize(
    "answer",
    ["Within 30 days.", "Within 30 days. [expenses/travel-deadline]"],
)
def test_answer_has_one_numbered_citation_per_source(answer):
    formatted = ui.format_answer(answer, [SOURCE])
    assert formatted.count(">[1]</abbr>") == 1
    assert "[expenses/travel-deadline]" not in formatted
    assert 'title="expenses.txt · Travel expense claims"' in formatted
    assert "Submit claims within 30 calendar days." not in formatted
    assert ui.format_answer(answer, []) == answer


def test_multiple_sources_keep_inline_positions_without_links():
    other_source = {
        **SOURCE,
        "chunk_id": "expenses/medical-deadline",
        "text": "Medical claims\nSubmit claims within 60 calendar days.",
    }
    answer = "Travel: 30 days. [expenses/travel-deadline]\nMedical: 60 days. [expenses/medical-deadline]"
    sources = [SOURCE, other_source]
    formatted = ui.format_answer(answer, sources)
    assert formatted.startswith("Travel: 30 days. <abbr")
    assert ">[1]</abbr>\nMedical: 60 days. <abbr" in formatted
    assert formatted.endswith(">[2]</abbr>")
    assert "href=" not in formatted


def test_citation_html_escapes_answer_and_source_text():
    source = {**SOURCE, "text": 'Policy "quoted" <script>alert(1)</script>'}
    formatted = ui.format_answer("<img src=x onerror=alert(1)> & policy", [source])
    assert "<img" not in formatted
    assert "<script>" not in formatted
    assert "&lt;img" in formatted
    assert "&quot;quoted&quot;" in formatted


def test_ui_cancel_allows_next_question(monkeypatch):
    at = app(monkeypatch)
    at.chat_input[0].set_value("When?").run()
    next(b for b in at.button if b.label == "Cancel question").click().run()
    assert FakeRun.calls[-1] == ("resume", "", True)
    assert not at.session_state["run"].pending
    assert not at.chat_input[0].disabled
    at.chat_input[0].set_value("What is the leave policy?").run()
    assert FakeRun.calls[-1] == ("start", "What is the leave policy?")
    assert not at.exception
