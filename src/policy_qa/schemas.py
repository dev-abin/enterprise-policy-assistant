"""Validated agent payloads. See docs/messages.md for the wire envelope."""
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, model_validator


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Evidence(StrictModel):
    chunk_id: str
    document_id: str
    section_id: str
    text: str


class Search(StrictModel):
    query: str = Field(min_length=1, max_length=1000)
    k: int = Field(default=3, ge=1, le=3)


class Clarification(StrictModel):
    interpretation: str
    question: str = Field(min_length=1)
    options: list[str]


class Research(StrictModel):
    scope_check: str = Field(description="Briefly identify the policy types in evidence and whether the user has specified the applicable type. If not, state the missing user detail before choosing an action.")
    action: Literal["write", "clarify"]
    source_ids: list[str]
    gaps: list[str]
    clarification: Clarification = Field(default_factory=lambda: Clarification(interpretation="", question="Not required", options=[]))

    @model_validator(mode="after")
    def check_clarification(self):
        if self.action == "clarify" and self.clarification is None:
            raise ValueError("clarify requires a clarification question")
        return self


class Draft(StrictModel):
    answer: str = Field(min_length=1)
    source_ids: list[str]
    abstain: bool


class Review(StrictModel):
    scope_check: str = Field(description="State whether the draft answers a confirmed user scope or lists alternatives because the user's scope is missing.")
    verdict: Literal["accept", "retrieve", "revise", "clarify", "abstain"]
    feedback: str
    source_ids: list[str]
    clarification: Clarification = Field(default_factory=lambda: Clarification(interpretation="", question="Not required", options=[]))

    @model_validator(mode="after")
    def check_clarification(self):
        if self.verdict == "clarify" and self.clarification is None:
            raise ValueError("clarify requires a clarification question")
        return self


class HumanReply(StrictModel):
    action: Literal["confirm", "correct", "cancel"]
    text: str = Field(default="", max_length=2000)

    @model_validator(mode="after")
    def check_text(self):
        if self.action != "cancel" and not self.text.strip():
            raise ValueError("A nonempty clarification reply is required")
        return self


class Final(StrictModel):
    status: Literal["answered", "abstained", "cancelled"]
    answer: str
    source_ids: list[str]


class Event(StrictModel):
    run_id: str
    message_id: str
    sequence: int
    timestamp: str
    sender: str
    recipient: str
    kind: Literal["question", "tool_call", "tool_result", "evidence", "draft", "review", "clarification_request", "clarification_response", "final", "error", "model_call", "metadata"]
    payload: dict
