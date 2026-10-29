"""Coordinate policy agents, human clarification, and bounded correction loops."""

import re
from typing import Literal, TypedDict

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command, interrupt

from .limits import MAX_CLARIFICATIONS, MAX_CORRECTIONS, MAX_SEARCHES
from .schemas import Final, HumanReply

ABSTENTION = "I couldn't find enough information in the available policies to answer your question."


class State(TypedDict, total=False):
    """Hold the question, evidence, agent outputs, and workflow progress."""

    question: str
    scope: str
    evidence: list[dict]
    research: dict
    draft: dict
    feedback: str
    clarification: dict
    clarifications: int
    corrections: int
    searches: int
    final: dict


def build_graph(agents, trace):
    """Build the agent workflow with in-memory checkpoints for pause and resume."""

    def abstain(reason, update=None, *, answer=ABSTENTION):
        """Prepare an unsupported-answer response and route to completion."""
        trace.emit(
            "orchestrator", "orchestrator", "metadata", {"abstention_reason": reason}
        )
        return Command(
            update={
                **(update or {}),
                "final": Final(
                    status="abstained", answer=answer, source_ids=[]
                ).model_dump(),
            },
            goto="finish",
        )

    def clarification_route(state, question, update=None):
        """Request human clarification unless the clarification limit is reached."""
        if state["clarifications"] >= MAX_CLARIFICATIONS:
            return abstain(
                "The question's applicable scope remains unclear after clarification.",
                update,
                answer="I couldn't determine which policy applies. Please rephrase your question with more detail.",
            )
        trace.emit("orchestrator", "human", "clarification_request", question)
        return Command(
            update={**(update or {}), "clarification": question.model_dump()},
            goto="clarify",
        )

    def research(state) -> Command[Literal["writer", "clarify", "finish"]]:
        """Gather evidence within the search budget and select the next step."""
        if state["searches"] >= MAX_SEARCHES:
            return abstain("The bounded search budget was exhausted.")
        result, evidence = agents.research(state)
        update = {
            "evidence": evidence,
            "research": result.model_dump(),
            "searches": state["searches"] + 1,
        }
        if result.action == "clarify":
            return clarification_route(state, result.clarification, update)
        return Command(update=update, goto="writer")

    def clarify(state) -> Command[Literal["researcher", "finish"]]:
        """Pause for a human reply, then cancel or restart research with its scope."""
        # This node restarts on resume. Do not perform effects before interrupt().
        reply = HumanReply.model_validate(interrupt(state["clarification"]))
        trace.emit("human", "researcher", "clarification_response", reply)
        if reply.action == "cancel":
            return Command(
                update={
                    "final": Final(
                        status="cancelled", answer="Question cancelled.", source_ids=[]
                    ).model_dump(),
                },
                goto="finish",
            )
        return Command(
            update={
                "scope": "\n".join(
                    part
                    for part in (state.get("scope", ""), reply.text.strip())
                    if part
                ),
                "clarifications": state["clarifications"] + 1,
                "draft": {},
                "evidence": [],
                "research": {},
                "feedback": "",
            },
            goto="researcher",
        )

    def writer(state):
        """Draft an answer and send it to the verifier."""
        result = agents.write(state)
        return {"draft": result.model_dump()}

    def verifier(
        state,
    ) -> Command[Literal["researcher", "writer", "clarify", "finish"]]:
        """Check citations and route the review within the correction limit."""
        draft = state["draft"]
        valid = {e["chunk_id"] for e in state["evidence"]}
        cited = set(re.findall(r"\[([^\]]+/[^\]]+)\]", draft["answer"]))
        invalid = (
            not set(draft["source_ids"]) <= valid
            or not cited <= valid
            or (not draft["abstain"] and not draft["source_ids"])
        )
        if invalid:
            # Deterministic guard prevents a model from accepting fabricated IDs.
            verdict, feedback = (
                "revise",
                "Use supporting evidence IDs in source_ids; any inline citations must also reference valid evidence.",
            )
            trace.emit(
                "orchestrator",
                "writer",
                "review",
                {"verdict": verdict, "feedback": feedback, "source_ids": []},
            )
        else:
            review = agents.verify(state)
            verdict, feedback = review.verdict, review.feedback
            if verdict == "clarify":
                return clarification_route(state, review.clarification)
        if verdict == "accept":
            return Command(
                update={
                    "final": Final(
                        status="abstained" if draft["abstain"] else "answered",
                        answer=draft["answer"],
                        source_ids=draft["source_ids"],
                    ).model_dump(),
                },
                goto="finish",
            )
        if verdict == "abstain":
            # Review feedback is diagnostic, not independently verified answer text.
            # Keep it in the trace; do not promote its process claims to user output.
            return abstain(
                "The verifier could not establish support in the retrieved policy sections."
            )
        if state["corrections"] >= MAX_CORRECTIONS:
            return abstain(
                "The draft could not be verified within the correction limit."
            )
        return Command(
            update={"feedback": feedback, "corrections": state["corrections"] + 1},
            goto="researcher" if verdict == "retrieve" else "writer",
        )

    def finish(state):
        """Record the final answer, abstention, or cancellation in the trace."""
        trace.emit(
            "orchestrator", "user", "final", Final.model_validate(state["final"])
        )
        return {}

    graph = StateGraph(State)
    graph.add_node("researcher", research)
    graph.add_node("clarify", clarify)
    graph.add_node("writer", writer)
    graph.add_node("verifier", verifier)
    graph.add_node("finish", finish)

    graph.add_edge(START, "researcher")
    graph.add_edge("writer", "verifier")
    graph.add_edge("finish", END)
    return graph.compile(checkpointer=InMemorySaver())
