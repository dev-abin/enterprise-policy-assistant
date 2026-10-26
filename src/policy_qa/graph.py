import re
from typing import TypedDict
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.types import interrupt
from .schemas import HumanReply, Final

ABSTENTION = "The supplied policies do not provide enough information for a supported answer."


class State(TypedDict, total=False):
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
    next: str
    final: dict


def build_graph(agents, trace):
    def abstain(reason):
        return {"final": Final(status="abstained", answer=ABSTENTION + " " + reason, source_ids=[]).model_dump(), "next": "finish"}

    def clarification_route(state, question):
        if state["clarifications"] >= 1:
            return abstain("The question's applicable scope remains unclear after clarification.")
        trace.emit("orchestrator", "human", "clarification_request", question)
        return {"clarification": question.model_dump(), "next": "clarify"}

    def research(state):
        if state["searches"] >= 3:
            return abstain("The bounded search budget was exhausted.")
        result, evidence = agents.research(state)
        update = {"evidence": evidence, "research": result.model_dump(), "searches": state["searches"] + 1}
        if result.action == "clarify":
            return {**update, **clarification_route(state, result.clarification)}
        return {**update, "next": "writer"}

    def clarify(state):
        # This node restarts on resume. Do not perform effects before interrupt().
        reply = HumanReply.model_validate(interrupt(state["clarification"]))
        trace.emit("human", "researcher", "clarification_response", reply)
        if reply.action == "cancel":
            return {"next": "finish", "final": Final(status="cancelled", answer="Question cancelled.", source_ids=[]).model_dump()}
        return {"scope": reply.text.strip(), "clarifications": state["clarifications"] + 1,
                "draft": {}, "evidence": [], "research": {}, "feedback": "", "next": "researcher"}

    def writer(state):
        result = agents.write(state)
        return {"draft": result.model_dump(), "next": "verifier"}

    def verifier(state):
        draft = state["draft"]
        valid = {e["chunk_id"] for e in state["evidence"]}
        cited = set(re.findall(r"\[([^\]]+/[^\]]+)\]", draft["answer"]))
        invalid = (not set(draft["source_ids"]) <= valid or not cited <= valid
                   or (not draft["abstain"] and not draft["source_ids"]))
        if invalid:
            # Deterministic guard prevents a model from accepting fabricated IDs.
            verdict, feedback = "revise", "Use supporting evidence IDs in source_ids; any inline citations must also reference valid evidence."
            trace.emit("orchestrator", "writer", "review", {"verdict": verdict, "feedback": feedback, "source_ids": []})
        else:
            review = agents.verify(state)
            verdict, feedback = review.verdict, review.feedback
            if verdict == "clarify":
                return clarification_route(state, review.clarification)
        if verdict == "accept":
            return {"next": "finish", "final": Final(status="abstained" if draft["abstain"] else "answered",
                answer=draft["answer"], source_ids=draft["source_ids"]).model_dump()}
        if verdict == "abstain":
            # Review feedback is diagnostic, not independently verified answer text.
            # Keep it in the trace; do not promote its process claims to user output.
            return abstain("The verifier could not establish support in the retrieved policy sections.")
        if state["corrections"] >= 1:
            return abstain("The draft could not be verified within the correction limit.")
        return {"feedback": feedback, "corrections": state["corrections"] + 1,
                "next": "researcher" if verdict == "retrieve" else "writer"}

    def finish(state):
        trace.emit("orchestrator", "user", "final", Final.model_validate(state["final"]))
        return {}

    graph = StateGraph(State)
    for name, node in (("researcher", research), ("clarify", clarify), ("writer", writer), ("verifier", verifier), ("finish", finish)):
        graph.add_node(name, node)
    graph.add_edge(START, "researcher")
    for name in ("researcher", "clarify", "writer", "verifier"):
        graph.add_conditional_edges(name, lambda state: state["next"],
                                    {key: key for key in ("researcher", "writer", "verifier", "clarify", "finish")})
    graph.add_edge("finish", END)
    return graph.compile(checkpointer=InMemorySaver())
