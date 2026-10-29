# Evaluation and error analysis

## Frozen evaluation

Implementation evaluated: commit `1c0adf84e52e581e5f17193f608f1cbde8641e30`. Data fixtures were committed before development in `04fb44e`. The eight held-out questions were run once after development checks. The system received the policy corpus but not expected answers. No model weights were trained.

Model: installed `qwen3.5:4b`, digest `2a654d98e6fba55d452b7043684e9b57a947e393bbffa62485a7aac05ee4eefd`. Ollama 0.34.4, Python 3.12.10, RTX 4060 Laptop 8 GB, approximately 32 GB system RAM. The ambiguous case used a predefined simulated reply containing only the missing user circumstance.

| Metric | Three-agent graph |
|---|---:|
| Overall correct responses | 7/8 (87.5%) |
| Supported policy claims in non-abstaining answers | 16/16 |
| Correct abstentions on unsupported questions | 2/2 |
| Unnecessary abstentions on answerable questions | 0/6 |
| Mean elapsed time per question | 8.21 s |
| Median elapsed time per question | 7.44 s |
| Total model calls | 34 |
| Clarification on ambiguous access question | Yes, then resumed |

Counts were reviewed by the coding assistant against source text, not by an independent human or a blinded judge. `reviewed_scores.json` records the reviewed claims and per-case decisions; `summarize_results.py` aggregates those labels into `evaluation.json`. The aggregation is reproducible; semantic review is not an automatic benchmark. Citation support excludes abstentions/process commentary but overall correctness includes false extra assertions, which explains the differing scores.

Timing is one local run, with warmed model state and simulated evaluation replies; it excludes real human waiting and initial model/index download. It is not a hardware benchmark. The cold-start smoke test took approximately 74 seconds including about 45 seconds of model loading; warm execution was much faster. The four policies are short and simple, and evaluation is question-level holdout with some shared policy facts. Eight examples do not establish general superiority or production accuracy.

## Held-out failure and subsequent fix

`eval-08` asked for the daily international-travel meal allowance, which is absent. The graph correctly abstained. However, it copied verifier feedback into its final answer, including: “No search for a specific monetary policy document was performed or indicated as available.” The actual tool query was `daily meal allowance amount international travel`. This unnecessary process assertion was unsupported, so the graph's response was marked incorrect overall despite its correct abstention.

Root cause: diagnostic feedback was promoted into user-facing text without verification. The verifier reviewed the writer's draft but not the new text introduced by the finalization node.

After recording the frozen results, finalization was changed to use a fixed evidence-limitation statement for verifier-requested abstentions. Internal feedback stays in execution traces instead of being appended to the answer. A focused test covers this fix. A separate model regression check was also run during development; its result and trace have been archived locally rather than included in the submission. The original 7/8 score is preserved; the regression is not a fresh held-out evaluation.

## Development failures

Development exposed the following failures. Intermediate development runs have been archived locally rather than included in the submission:

- Initially the writer supplied correct structured source IDs but omitted inline brackets. A strict formatting guard caused unnecessary abstention. Source IDs now drive the UI citations, and application checks reject nonexistent IDs.
- Both tested 4B and 9B variants initially answered an ambiguous claim question with a menu of alternatives. An explicit scope-check field before the routing decision produced the required clarification behavior; 9B was not selected simply because it was larger.
- A nullable clarification object remained null even when the model selected `clarify`. A consistently shaped object is now used, with a non-displayed placeholder for other decisions.
- The verifier requested extra details beyond the user's question, exhausting the correction limit. Its instructions were narrowed to correctness and completeness for the actual request.
- The researcher sometimes cited a document name instead of a section ID. Model output schemas now restrict source IDs to the exact retrieved chunk IDs, with application checks afterward.

All four final development cases completed as intended. The final held-out run used the resulting configuration, with no question-specific branches or hard-coded policy answers.

## Required demonstration traces

1. **Success, full three-agent flow:** [traces/success.jsonl](traces/success.jsonl). Explicit travel-expense deadline question; retrieval, researcher assessment, writer draft, verifier acceptance, final response. No clarification required.
2. **Ambiguous-request edge case with a real human reply:** [traces/clarification.jsonl](traces/clarification.jsonl). Question: “When should I submit my claim?” The agent asked which claim type. The actual user selected “Travel expense”; the same graph run resumed and answered with the 30-calendar-day rule. This trace records real human input, not an evaluation fixture.

An additional historical Streamlit integration check used an explicitly labelled automated reply. It verified chat interruption, resume, source display, disabled input after completion in the earlier interface, and no additional model calls on rerender. At that stage the focused suite had 13 passing tests. Its trace has been archived locally; the current UI allows a new question directly after completion, and the automated suite has since expanded.

## Retained submission evidence

`eval-agents.json` retains the original evaluation outputs byte for byte under a shorter filename. `reviewed_scores.json` supplies the reviewed labels, and `scripts/summarize_results.py` reproduces `evaluation.json` from those two files. The answers, scores, model metadata, and timings are unchanged.

Only the two full demonstration traces above are included. The `trace` fields inside the evaluation outputs preserve original per-case run paths; those detailed logs are archived locally and are not repository links. Development runs, ordinary chat sessions, and regression logs are excluded from the submitted results folder. The retained traces preserve their original event IDs and contents and describe the earlier implementation, not a fresh execution of the current revision.

## What this establishes

### Subsequent prompt revision

On 27 October 2026, system prompts were moved to `src/policy_qa/prompts.py` and revised as prompt version 2. Role tasks, evidence boundaries, clarification versus missing-fact decisions, and schema contracts are now explicit. Retrieval uses the same shared evidence rules. New graph traces record the prompt version.

Development checks of the four existing cases with this prompt revision confirmed the direct deadline, clarification/resume, missing-policy abstention and incident-contact behaviors against the source sections. The clarification reply was simulated, as recorded in the archived run. The 13 focused tests at that stage also passed. These are development checks, not a fresh held-out evaluation or evidence of an accuracy improvement. The frozen scores above describe the original evaluated configuration.

The implementation demonstrates the Track A collaboration, tool-use, observability, and human-checkpoint behaviors on the recorded cases. The graph provides explicit control over clarification and review, with additional model calls and latency. The small synthetic evaluation does not establish production reliability or prove that separate agents improve answer quality.

Before production, use real permissioned policies, independently review evaluation labels, test contradictory versions and prompt injection, and add retrieval-time authorization and durable session state. These are limitations and future alternatives, not implemented features.
