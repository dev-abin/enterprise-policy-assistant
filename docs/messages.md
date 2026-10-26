# Agent messages and execution

Each JSONL event has `run_id: str`, `message_id: str`, `sequence: int`, `timestamp: ISO-8601 str`, `sender: str`, `recipient: str`, `kind: enum`, and `payload: object`. The envelope is validated by `schemas.Event`. Decision payloads are validated by the corresponding Pydantic classes before graph transitions. Tool arguments use `Search`; citation IDs are constrained to retrieved chunks in the model output schema and checked again in application code.

Participants: `user`, `human`, `researcher`, `writer`, `verifier`, `retrieval_tool`, `orchestrator`. Self-addressed `model_call` events expose each role's input and output; they are not inter-agent messages. Inter-agent `evidence`, `draft`, and `review` events show collaboration separately.

| Kind | Payload type / fields |
|---|---|
| question | `{text: str}` |
| tool_call | `Search(query: str, k: int[1..3])`; only search_documents is allowed |
| tool_result | `{evidence: list[Evidence]}` |
| evidence | `{assessment: Research, evidence: list[Evidence]}` |
| draft | `Draft(answer: str, source_ids: list[str], abstain: bool)` |
| review | `Review(scope_check: str, verdict: accept/retrieve/revise/clarify/abstain, feedback: str, source_ids: list[str], clarification: Clarification)`; deterministic citation guard emits verdict/feedback/IDs |
| clarification_request | `Clarification(interpretation: str, question: str, options: list[str])` |
| clarification_response | `HumanReply(action: confirm/correct/cancel, text: str)` |
| final | `Final(status: answered/abstained/cancelled, answer: str, source_ids: list[str])` |
| error | `{stage: str, code: str, message: str}` for graph errors |
| model_call | full request/schema/messages, response, elapsed seconds, input/output token counts, done reason |
| metadata | model and digest, corpus hash, prompt version, execution limits, reply actor |

`Evidence`: `chunk_id`, `document_id`, `section_id`, `text` (all strings).
`Research`: `scope_check: str`, `action: write/clarify`, `source_ids: list[str]`, `gaps: list[str]`, `clarification: Clarification`.

The brief scope check is an observable decision summary, not a request for hidden chain-of-thought. A clarification object is always present in structured model output because the installed local model failed to populate the nullable form reliably. For a non-clarification decision its question is `Not required`, with empty interpretation/options; it is not displayed.

Example researcher-to-writer payload:

```json
{
  "assessment": {
    "scope_check": "The user explicitly asks about travel expenses.",
    "action": "write",
    "source_ids": ["expenses/travel-deadline"],
    "gaps": [],
    "clarification": {"interpretation": "", "question": "Not required", "options": []}
  },
  "evidence": [{"chunk_id": "expenses/travel-deadline", "document_id": "expenses", "section_id": "travel-deadline", "text": "Employees must submit travel expense claims within 30 calendar days after returning from the trip."}]
}
```

Example verifier-to-writer payload:

```json
{
  "scope_check": "Travel expense claim is confirmed.",
  "verdict": "revise",
  "feedback": "The draft says working days; the source specifies calendar days.",
  "source_ids": ["expenses/travel-deadline"],
  "clarification": {"interpretation": "", "question": "Not required", "options": []}
}
```

These examples illustrate the schema; actual outputs are in `results/traces/`.

The graph permits three retrieval calls, one corrective review loop, and one clarification exchange. A separate human node calls LangGraph `interrupt()`; `Command(resume=...)` continues the same thread. The reply is traced after the interrupt returns, avoiding duplicate events when the node restarts. New questions get fresh IDs and checkpoints. Failures are logged as errors, not silently converted into missing-policy answers. In-memory checkpoints do not survive browser session loss or process restart.
