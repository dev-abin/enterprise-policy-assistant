"""Validated agent payloads. See DESIGN.md for the agent message contract."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class StrictModel(BaseModel):
    """Provide a shared model that rejects unexpected fields."""

    model_config = ConfigDict(extra="forbid")


class Evidence(StrictModel):
    """Represent a retrieved policy section with its source identifiers."""

    chunk_id: str
    document_id: str
    section_id: str
    text: str


class Search(StrictModel):
    """Define a policy search query and the number of sections to retrieve."""

    query: str = Field(min_length=1, max_length=1000)
    k: int = Field(default=3, ge=1, le=3)


class Clarification(StrictModel):
    """Describe the agent's interpretation and a question for the user."""

    interpretation: str
    question: str = Field(min_length=1)
    options: list[str]


class Research(StrictModel):
    """Capture the researcher's evidence assessment and next action."""

    scope_check: str = Field(
        description="Briefly identify the policy types in evidence and whether the user has specified the applicable type. If not, state the missing user detail before choosing an action."
    )
    action: Literal["write", "clarify"]
    source_ids: list[str]
    gaps: list[str]
    clarification: Clarification = Field(
        default_factory=lambda: Clarification(
            interpretation="", question="Not required", options=[]
        )
    )


class Draft(StrictModel):
    """Hold the writer's proposed answer, source references, and abstention flag."""

    answer: str = Field(min_length=1)
    source_ids: list[str]
    abstain: bool


class Review(StrictModel):
    """Capture the verifier's verdict, feedback, and any clarification request."""

    scope_check: str = Field(
        description="State whether the draft answers a confirmed user scope or lists alternatives because the user's scope is missing."
    )
    verdict: Literal["accept", "retrieve", "revise", "clarify", "abstain"]
    feedback: str
    source_ids: list[str]
    clarification: Clarification = Field(
        default_factory=lambda: Clarification(
            interpretation="", question="Not required", options=[]
        )
    )


class HumanReply(StrictModel):
    """Represent the user's confirmation, correction, or cancellation."""

    action: Literal["confirm", "correct", "cancel"]
    text: str = Field(default="", max_length=2000)

    @model_validator(mode="after")
    def check_text(self):
        if self.action != "cancel" and not self.text.strip():
            raise ValueError("A nonempty clarification reply is required")
        return self


class Final(StrictModel):
    """Hold the completed run's status, answer, and source references."""

    status: Literal["answered", "abstained", "cancelled"]
    answer: str
    source_ids: list[str]


class Event(StrictModel):
    """Record a trace message with its sender, recipient, timing, and payload."""

    run_id: str
    message_id: str
    sequence: int
    timestamp: str
    sender: str
    recipient: str
    kind: Literal[
        "question",
        "tool_call",
        "tool_result",
        "evidence",
        "draft",
        "review",
        "clarification_request",
        "clarification_response",
        "final",
        "error",
        "model_call",
        "metadata",
    ]
    payload: dict
