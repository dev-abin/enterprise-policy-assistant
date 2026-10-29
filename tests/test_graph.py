from types import SimpleNamespace

import pytest
from langgraph.types import Command

from policy_qa.graph import ABSTENTION, build_graph
from policy_qa.schemas import Clarification, Draft, HumanReply, Research, Review
from policy_qa.traces import Trace

EVIDENCE = [
    {
        "chunk_id": "expenses/travel",
        "document_id": "expenses",
        "section_id": "travel",
        "text": "Travel claims: 30 calendar days.",
    }
]


class Agents:
    def __init__(
        self, clarify=False, verdict="accept", invalid=False, always_clarify=False
    ):
        self.calls = []
        self.clarify, self.verdict, self.invalid, self.always_clarify = (
            clarify,
            verdict,
            invalid,
            always_clarify,
        )

    def research(self, state):
        self.calls.append(("researcher", state.get("scope")))
        needs = self.always_clarify or (self.clarify and not state.get("scope"))
        return Research(
            scope_check="test",
            action="clarify" if needs else "write",
            source_ids=[],
            gaps=[],
            clarification=Clarification(
                interpretation="Claim unspecified",
                question="Which claim?",
                options=["Travel", "Medical"],
            )
            if needs
            else Clarification(interpretation="", question="Not required", options=[]),
        ), EVIDENCE

    def write(self, state):
        self.calls.append(("writer", state.get("feedback")))
        return Draft(
            answer="Within 30 calendar days.",
            source_ids=["invented/id" if self.invalid else "expenses/travel"],
            abstain=False,
        )

    def verify(self, state):
        self.calls.append(("verifier", None))
        return Review(
            scope_check="test",
            verdict=self.verdict,
            feedback="Check evidence.",
            source_ids=[],
        )


def setup(tmp_path, agents):
    trace = Trace(tmp_path / "trace.jsonl", "test")
    graph = build_graph(agents, trace)
    config = {"configurable": {"thread_id": "test"}, "recursion_limit": 25}
    initial = {
        "question": "When?",
        "scope": "",
        "clarifications": 0,
        "corrections": 0,
        "searches": 0,
        "feedback": "",
    }
    return graph, trace, config, initial


def test_clear_question_finishes_without_interrupt(tmp_path):
    agents = Agents()
    graph, trace, config, state = setup(tmp_path, agents)
    result = graph.invoke(state, config)
    assert result["final"]["status"] == "answered"
    assert [x[0] for x in agents.calls] == ["researcher", "writer", "verifier"]
    assert sum(e["kind"] == "final" for e in trace.events) == 1


def test_pause_resume_uses_same_run_and_scope(tmp_path):
    agents = Agents(clarify=True)
    graph, trace, config, state = setup(tmp_path, agents)
    first = graph.invoke(state, config)
    assert first["__interrupt__"]
    assert len(agents.calls) == 1  # no writer or verifier before human input
    assert not any(e["kind"] == "final" for e in trace.events)
    final = graph.invoke(
        Command(resume={"action": "correct", "text": "Travel"}), config
    )
    assert final["final"]["status"] == "answered"
    assert agents.calls[1] == ("researcher", "Travel")
    assert sum(e["kind"] == "clarification_request" for e in trace.events) == 1
    assert sum(e["kind"] == "clarification_response" for e in trace.events) == 1


def test_cancel_never_writes_answer(tmp_path):
    agents = Agents(clarify=True)
    graph, _trace, config, state = setup(tmp_path, agents)
    graph.invoke(state, config)
    result = graph.invoke(Command(resume={"action": "cancel", "text": ""}), config)
    assert result["final"]["status"] == "cancelled"
    assert len(agents.calls) == 1


@pytest.mark.parametrize("verdict", ["retrieve", "revise"])
def test_corrections_are_bounded(tmp_path, verdict):
    agents = Agents(verdict=verdict)
    graph, trace, config, state = setup(tmp_path, agents)
    result = graph.invoke(state, config)
    assert result["final"]["status"] == "abstained"
    assert result["final"]["answer"] == ABSTENTION
    assert any("abstention_reason" in e["payload"] for e in trace.events)
    assert result["corrections"] == 3
    assert result["searches"] <= 3
    assert len([x for x in agents.calls if x[0] == "writer"]) == (
        3 if verdict == "retrieve" else 4
    )


@pytest.mark.parametrize(
    "draft_update",
    [
        {"source_ids": ["invented/id"]},
        {"answer": "Within 30 calendar days. [invented/id]"},
        {"source_ids": []},
    ],
)
def test_invalid_citations_cannot_be_accepted(tmp_path, draft_update):
    agents = Agents()
    write = agents.write
    agents.write = lambda state: write(state).model_copy(update=draft_update)
    graph, _trace, config, state = setup(tmp_path, agents)
    result = graph.invoke(state, config)
    assert result["final"]["status"] == "abstained"
    assert not any(x[0] == "verifier" for x in agents.calls)


def test_verifier_can_pause_then_accept_clarified_answer(tmp_path):
    agents = Agents()
    verify = agents.verify

    def review(state):
        result = verify(state)
        if not state.get("scope"):
            return result.model_copy(
                update={
                    "verdict": "clarify",
                    "clarification": Clarification(
                        interpretation="Claim unspecified",
                        question="Which claim?",
                        options=["Travel", "Medical"],
                    ),
                }
            )
        return result

    agents.verify = review
    graph, trace, config, state = setup(tmp_path, agents)
    first = graph.invoke(state, config)
    assert first["__interrupt__"]
    assert [name for name, _ in agents.calls] == ["researcher", "writer", "verifier"]
    assert not any(e["kind"] == "final" for e in trace.events)

    final = graph.invoke(
        Command(resume={"action": "correct", "text": "Travel"}), config
    )
    assert final["final"]["status"] == "answered"
    assert final["scope"] == "Travel"
    assert [name for name, _ in agents.calls] == [
        "researcher",
        "writer",
        "verifier",
    ] * 2
    assert sum(e["kind"] == "final" for e in trace.events) == 1


def test_three_clarifications_preserve_replies_and_search_budget(tmp_path):
    agents = Agents(always_clarify=True)
    graph, trace, config, state = setup(tmp_path, agents)
    result = graph.invoke(state, config)
    for reply in ("Travel", "Domestic", "Employee"):
        assert result.get("__interrupt__")
        result = graph.invoke(
            Command(resume={"action": "correct", "text": reply}), config
        )
    assert not result.get("__interrupt__")
    assert result["final"]["status"] == "abstained"
    assert result["clarifications"] == 3
    assert result["searches"] == 3
    assert result["scope"] == "Travel\nDomestic\nEmployee"
    assert sum(e["kind"] == "clarification_request" for e in trace.events) == 3


def test_no_fourth_clarification(tmp_path):
    agents = Agents(always_clarify=True)
    graph, trace, config, state = setup(tmp_path, agents)
    state["clarifications"] = 3
    result = graph.invoke(state, config)
    assert not result.get("__interrupt__")
    assert result["final"]["status"] == "abstained"
    assert not any(e["kind"] == "clarification_request" for e in trace.events)
    assert result["searches"] == 1
    assert result["evidence"] == EVIDENCE


def test_blank_reply_is_not_approval():
    with pytest.raises(ValueError):
        HumanReply(action="confirm", text=" ")


def test_abstention_does_not_publish_unverified_diagnostics(tmp_path):
    agents = Agents()
    agents.verify = lambda state: Review(
        scope_check="Scope clear",
        verdict="abstain",
        feedback="No search was performed. This is an unverified process claim.",
        source_ids=[],
    )
    graph, trace, config, state = setup(tmp_path, agents)
    result = graph.invoke(state, config)
    assert result["final"]["status"] == "abstained"
    assert "No search" not in result["final"]["answer"]
    assert result["final"]["answer"] == ABSTENTION
    assert any(
        "verifier" in e["payload"].get("abstention_reason", "") for e in trace.events
    )
    assert not result["final"]["source_ids"]


def test_trace_never_overwrites(tmp_path):
    Trace(tmp_path / "x.jsonl", "a")
    with pytest.raises(FileExistsError):
        Trace(tmp_path / "x.jsonl", "b")


def test_tool_failure_is_error_not_abstention(tmp_path):
    from policy_qa.service import Run

    class BrokenLLM:
        model, digest = "fake", "fake"

        def search_call(self, context, trace):
            raise ConnectionError("Ollama unavailable")

    run = Run(BrokenLLM(), SimpleNamespace(corpus_hash="test"), trace_dir=tmp_path)
    with pytest.raises(ConnectionError):
        run.start("What is the policy?")
    assert run.failed
    assert run.trace.events[-1]["kind"] == "error"
    assert not any(e["kind"] == "final" for e in run.trace.events)
