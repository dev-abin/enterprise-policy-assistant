"""Agent execution and validated agent-to-agent outputs."""

from .prompts import RESEARCH, VERIFY, WRITE
from .schemas import Draft, Research, Review


def context(state):
    """Collect the question, confirmed scope, evidence and agent feedback."""
    return {
        "question": state["question"],
        "user_clarification": state.get("scope", ""),
        "reviewer_feedback": state.get("feedback", ""),
        "evidence": state.get("evidence", []),
        "researcher_assessment": state.get("research", {}),
    }


class Agents:
    """Run the researcher, writer and verifier and record their handoffs."""

    def __init__(self, llm, index, trace):
        """Connect the agents to the model, policy index and interaction trace."""
        self.llm, self.index, self.trace = llm, index, trace

    def research(self, state):
        """Retrieve policy evidence and decide whether user clarification is needed."""
        request = self.llm.search_call(context(state), self.trace)
        self.trace.emit("researcher", "retrieval_tool", "tool_call", request)
        evidence = self.index.search(request.query, request.k)
        self.trace.emit(
            "retrieval_tool", "researcher", "tool_result", {"evidence": evidence}
        )
        state = {**state, "evidence": evidence}
        result = self.llm.structured(
            "researcher", RESEARCH, context(state), Research, self.trace
        )
        self.trace.emit(
            "researcher",
            "writer" if result.action == "write" else "human",
            "evidence",
            {"assessment": result.model_dump(), "evidence": evidence},
        )
        return result, evidence

    def write(self, state):
        """Draft an evidence-based answer or explain why the evidence is insufficient."""
        result = self.llm.structured("writer", WRITE, context(state), Draft, self.trace)
        self.trace.emit("writer", "verifier", "draft", result)
        return result

    def verify(self, state):
        """Check the draft against policy evidence and select the next action."""
        result = self.llm.structured(
            "verifier",
            VERIFY,
            {**context(state), "draft": state["draft"]},
            Review,
            self.trace,
        )
        recipient = {
            "retrieve": "researcher",
            "revise": "writer",
            "clarify": "human",
        }.get(result.verdict, "orchestrator")
        self.trace.emit("verifier", recipient, "review", result)
        return result
