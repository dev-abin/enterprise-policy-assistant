"""UI event routing tests; no model calls and no simulated human claims."""
from types import SimpleNamespace
from pathlib import Path
from streamlit.testing.v1 import AppTest
import policy_qa.ui as ui


class FakeRun:
    calls = []
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
        self.state = {"final": {"answer": "Cancelled" if cancel else "30 calendar days", "source_ids": []}, "evidence": []}


def app(monkeypatch):
    FakeRun.calls = []
    monkeypatch.setattr(ui, "Run", FakeRun)
    monkeypatch.setattr(ui, "PolicyIndex", lambda: object())
    monkeypatch.setattr(ui, "Ollama", lambda: object())
    return AppTest.from_file(Path(__file__).resolve().parents[1] / "app.py", default_timeout=15).run()


def test_ui_clarification_resume_and_rerender(monkeypatch):
    at = app(monkeypatch)
    at.chat_input[0].set_value("When should I claim?").run()
    assert not at.exception
    assert FakeRun.calls == [("start", "When should I claim?")]
    at.run()
    assert len(FakeRun.calls) == 1
    at.chat_input[0].set_value("Travel").run()
    assert FakeRun.calls[-1] == ("resume", "Travel", False)
    assert at.chat_input[0].disabled
    assert not at.exception
    at.run()
    assert len(FakeRun.calls) == 2


def test_ui_new_question_cancels_pending(monkeypatch):
    at = app(monkeypatch)
    at.chat_input[0].set_value("When?").run()
    next(b for b in at.button if b.label == "New question").click().run()
    assert FakeRun.calls[-1] == ("resume", "", True)
    assert not at.session_state["messages"]
    assert not at.exception
