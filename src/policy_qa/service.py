import uuid
from pathlib import Path

from langgraph.types import Command

from .agents import Agents
from .graph import build_graph
from .limits import (
    GRAPH_STEP_LIMIT,
    MAX_CLARIFICATIONS,
    MAX_CORRECTIONS,
    MAX_OUTPUT_REPAIRS,
    MAX_SEARCHES,
)
from .prompts import PROMPT_VERSION
from .retrieval import ROOT
from .schemas import HumanReply
from .traces import Trace


class Run:
    """Manage one policy question, its graph state, and its interaction trace."""

    def __init__(self, llm, index, trace_dir=None, prefix="live", actor="human"):
        """Set up the agents, graph, and trace for a new run."""
        self.id = prefix + "-" + uuid.uuid4().hex
        self.trace = Trace(
            Path(trace_dir or ROOT / "results/traces") / (self.id + ".jsonl"), self.id
        )
        self.trace.emit(
            "orchestrator",
            "orchestrator",
            "metadata",
            {
                "model": llm.model,
                "model_digest": llm.digest,
                "corpus_sha256": index.corpus_hash,
                "reply_actor": actor,
                "prompt_version": PROMPT_VERSION,
                "context_tokens": 4096,
                "limits": {
                    "searches": MAX_SEARCHES,
                    "clarifications": MAX_CLARIFICATIONS,
                    "corrections": MAX_CORRECTIONS,
                    "output_repairs": MAX_OUTPUT_REPAIRS,
                    "graph_steps": GRAPH_STEP_LIMIT,
                },
            },
        )
        self.graph = build_graph(Agents(llm, index, self.trace), self.trace)
        self.config = {
            "configurable": {"thread_id": self.id},
            "recursion_limit": GRAPH_STEP_LIMIT,
        }
        self.state = {}
        self.pending = None
        self.failed = False
        self.started = False

    def start(self, question):
        """Validate the question and start the graph with an empty evidence state."""
        if self.started:
            raise ValueError("This run has already started")
        if not question.strip() or len(question) > 2000:
            raise ValueError("Enter a question of 1–2000 characters")
        self.started = True
        self.trace.emit("user", "researcher", "question", {"text": question})
        return self._invoke(
            {
                "question": question,
                "scope": "",
                "evidence": [],
                "feedback": "",
                "clarifications": 0,
                "corrections": 0,
                "searches": 0,
            }
        )

    def resume(self, text="", cancel=False):
        """Continue a paused run with a clarification reply or cancellation."""
        if not self.pending or self.failed:
            raise ValueError("No resumable clarification is pending")
        reply = HumanReply(action="cancel" if cancel else "correct", text=text)
        return self._invoke(Command(resume=reply.model_dump()))

    def _invoke(self, value):
        """Execute the graph, refresh run state, and trace failures before re-raising."""
        try:
            result = self.graph.invoke(value, self.config)
            self.pending = (
                result["__interrupt__"][0].value
                if result.get("__interrupt__")
                else None
            )
            self.state = self.graph.get_state(self.config).values
            return self.state
        except Exception as error:
            self.failed = True
            self.pending = None
            self.trace.emit(
                "orchestrator",
                "user",
                "error",
                {"stage": "graph", "code": type(error).__name__, "message": str(error)},
            )
            raise
