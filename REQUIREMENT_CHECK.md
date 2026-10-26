# Requirement coverage

Checklist numbers match `DESIGN.md`. Status applies to local implementation, not final submission or a guaranteed passing assessment. Final publication, video, and PDF were explicitly deferred by the user.

| Item | Status and evidence |
|---|---|
| 1. One track/scenario and business problem | Covered: README, Track A + S2 policy Q&A. |
| 2. One S2 capability | Covered: question answering in app.py and src/policy_qa. |
| 3. Three collaborating agents | Covered: agents.py, graph.py; researcher, writer, verifier. |
| 4. Distinct roles and observable communication | Covered: role prompts, evidence/draft/review events; results/traces. |
| 5. Framework | Covered: LangGraph StateGraph, conditional edges, InMemorySaver. |
| 6. Message schema and examples | Covered: schemas.py and docs/messages.md. |
| 7. External tool | Covered: native search_documents tool call, validated execution against Chroma in agents.py. |
| 8. Human checkpoint | Covered: interrupt and Command resume in graph.py/service.py; real requester clarification in demo trace. |
| 9. Two full end-to-end traces | Covered: success and ambiguous-request edge case linked in results/error_analysis.md. |
| 10. Agentic versus simpler alternatives | Covered locally: README and error_analysis; baseline comparison does not show an accuracy benefit. Final PDF deferred. |
| 11. Framework choice/trade-offs | Covered locally: README and DESIGN.md. Final PDF deferred. |
| 12. Agent grouping rationale | Covered locally: README, three required roles and no extra manager. Final PDF deferred. |
| 13. Silent failure handling | Covered: schema/citation checks, bounded loops, tests, error_analysis; residual risks documented. |
| 14. Data source and suitability | Covered: data/README.md, four synthetic enterprise policy documents. |
| 15. Synthetic generation/distributions/limitations | Covered: scripts/generate_data.py and data/README.md. |
| 16. Hosted repository/reviewer access | Deferred. Local Git repository exists; no publication or access grant. |
| 17. README/reproduction | Covered: README.md, setup, data, tests, evaluation commands. |
| 18. Pinned dependencies and Python | Covered: requirements.txt and README (Python 3.12.10); pip check passed. |
| 19. Organized code/data/results/write-up | Local code, data, docs, tests, results organized. Final PDF write-up deferred. |
| 20. Iterative commits | Covered locally: separate fixture, implementation, and verification/documentation commits. |
| 21. Narrated video at most five minutes | Deferred. |
| 22. Video content and more-time alternatives | Reasoning/results/failures/alternatives documented in README, DESIGN, error_analysis; recording deferred. |
| 23. Video hosting and README URL | Deferred; README explicitly states no video URL yet. |
| 24. 1–2 page PDF, 11pt minimum, name/track | Deferred; not claimed complete. |
| 25. Write-up problem/domain section | Source material ready in README/DESIGN; final PDF deferred. |
| 26. Write-up decisions/alternatives section | Source material ready in README/DESIGN; final PDF deferred. |
| 27. Held-out results and error analysis | Covered locally: results/evaluation.json, reviewed_scores.json, error_analysis.md and raw runs. Final PDF deferred. |
| 28. Production consideration and limitation | Covered locally: permissions, durable state, synthetic-data limitations in README/error_analysis. Final PDF deferred. |
| 29. Receipt deadline and clarification window | Receipt timestamp unknown; compliance not asserted. |
| 30. Recruiter submission link and three deliverables | Deferred; nothing submitted. |
| 31. Tooling justification | Covered in README/DESIGN; local Ollama, Chroma/MiniLM, LangGraph, Streamlit. |
| 32. Framing evaluation criterion (25%) | Addressed in README/DESIGN. Actual reviewer score unknown. |
| 33. Algorithm/alternative criterion (30%) | Addressed in choice table and measured baseline comparison. Actual reviewer score unknown. |
| 34. Execution criterion (25%) | 13 focused tests passed; real model/UI execution verified. Actual reviewer score unknown. |
| 35. Evaluation/error criterion (10%) | Frozen runs, explicit labels, small-sample limits, original failure preserved after regression fix. Actual reviewer score unknown. |
| 36. Communication criterion (10%) | Local README/design/results prepared; final PDF/video deferred. Actual reviewer score unknown. |
| 37. Strong-submission signals | Local traces, call counts/latency, deployment/update discussion covered; no production infrastructure added. |

## Assumptions and limits

- English, short text policies; single local user/session; one question per run and one clarification exchange.
- Clarification lets the requester review/override scope before continuation; it does not ask them to validate answer correctness.
- Four policies, four development questions, eight held-out questions are choices, not mandated sizes. Some facts overlap across question-level splits.
- Same installed 4B model for all three roles; correlated errors remain possible. No additional model download or fine-tuning.
- Semantic scoring was reviewed by the coding assistant, not independently by a human. Scores and timing apply to one small local run.
- Held-out score remains 7/8 for agents versus 8/8 baseline. The discovered diagnostic-text problem was fixed afterward and checked as a regression, not relabelled as fresh held-out success.
- In-memory checkpoints do not survive process/session loss. Enterprise authorization and production recovery are not implemented.
- No submission, external messaging, repository publishing, video recording, or final PDF creation was performed.
