# Evaluation and error analysis

## Frozen evaluation

Implementation evaluated: commit `1c0adf84e52e581e5f17193f608f1cbde8641e30`. Data fixtures were committed before development in `04fb44e`. The eight held-out questions were run once per system after development checks. The system received the policy corpus but not expected answers. No model weights were trained.

Model: installed `qwen3.5:4b`, digest `2a654d98e6fba55d452b7043684e9b57a947e393bbffa62485a7aac05ee4eefd`. Ollama 0.34.4, Python 3.12.10, RTX 4060 Laptop 8 GB, approximately 32 GB system RAM. Both systems used identical model settings and corpus. The baseline used one fixed retrieval and one answer call. For its ambiguous case, the user clarification was supplied upfront; therefore that comparison tests answer quality with matched scope, not baseline clarification ability.

| Metric | Three-agent graph | Single-pass baseline |
|---|---:|---:|
| Overall correct responses | 7/8 (87.5%) | 8/8 (100%) |
| Supported policy claims in non-abstaining answers | 16/16 | 17/17 |
| Correct abstentions on unsupported questions | 2/2 | 2/2 |
| Unnecessary abstentions on answerable questions | 0/6 | 0/6 |
| Mean elapsed time per question | 8.21 s | 1.42 s |
| Median elapsed time per question | 7.44 s | 1.40 s |
| Total model calls | 34 | 8 |
| Clarification on ambiguous access question | Yes, then resumed | Not tested; supplied matched scope |

Counts were reviewed by the coding assistant against source text, not by an independent human or a blinded judge. `reviewed_scores.json` records the reviewed claims and per-case decisions; `summarize_results.py` aggregates those labels into `evaluation.json`. The aggregation is reproducible; semantic review is not an automatic benchmark. Citation support excludes abstentions/process commentary but overall correctness includes false extra assertions, which explains the differing scores.

Timing is one local run, with warmed model state and simulated evaluation replies; it excludes real human waiting and initial model/index download. It is not a hardware benchmark. The cold-start smoke test took approximately 74 seconds including about 45 seconds of model loading; warm execution was much faster. The four policies are short and simple, and evaluation is question-level holdout with some shared policy facts. Eight examples do not establish general superiority or production accuracy.

## Held-out failure and subsequent fix

`eval-08` asked for the daily international-travel meal allowance, which is absent. Both systems correctly abstained. However, the graph copied verifier feedback into its final answer, including: “No search for a specific monetary policy document was performed or indicated as available.” The actual tool query was `daily meal allowance amount international travel`. This unnecessary process assertion was unsupported, so the graph's response was marked incorrect overall despite its correct abstention.

Root cause: diagnostic feedback was promoted into user-facing text without verification. The verifier reviewed the writer's draft but not the new text introduced by the finalization node.

After recording the frozen results, finalization was changed to use a fixed evidence-limitation statement for verifier-requested abstentions. Full feedback remains available in the trace. A focused test and `scripts/regression_abstention.py` verify this fix. `post_evaluation_regression.json` records its outcome. The original 7/8 score is preserved; the regression is not a fresh held-out evaluation and no new 8/8 generalization claim is made.

The baseline attached unrelated retrieved IDs to its last abstention. It did not invent the requested amount, so this was recorded as an unnecessary citation choice rather than a wrong policy answer.

## Development failures

Saved development traces include unsuccessful runs as well as successful ones:

- Initially the writer supplied correct structured source IDs but omitted inline brackets. A strict formatting guard caused unnecessary abstention. Source IDs now drive the Sources panel, and application checks reject nonexistent IDs.
- Both tested 4B and 9B variants initially answered an ambiguous claim question with a menu of alternatives. An explicit scope-check field before the routing decision produced the required clarification behavior; 9B was not selected simply because it was larger.
- A nullable clarification object remained null even when the model selected `clarify`. A consistently shaped object is now used, with a non-displayed placeholder for other decisions.
- The verifier requested extra details beyond the user's question, exhausting the correction limit. Its instructions were narrowed to correctness and completeness for the actual request.
- The researcher sometimes cited a document name instead of a section ID. Model output schemas now restrict source IDs to the exact retrieved chunk IDs, with application checks afterward.

All four final development cases completed as intended. The final held-out run used the resulting configuration, with no question-specific branches or hard-coded policy answers.

## Required demonstration traces

1. **Success, full three-agent flow:** `traces/dev-3d7751895f054b168499251627d6083c.jsonl`. Explicit travel-expense deadline question; retrieval, researcher assessment, writer draft, verifier acceptance, final response. No clarification required.
2. **Ambiguous-request edge case with a real human reply:** `traces/demo-0a2a635d6a514254b2e533495f1776a8.jsonl`. Question: “When should I submit my claim?” The agent asked which claim type. The actual user selected “Travel expense”; the same graph run resumed and answered with the 30-calendar-day rule. This trace records real human input, not an evaluation fixture.

Additional live Streamlit integration check: `traces/ui-check-d7f2541fbe8549ad99fc88f9fdadfffe.jsonl`. Its reply is explicitly labelled automated. It verified chat interruption, resume, source display, disabled input after completion, and no additional model calls on rerender. The focused suite has 13 passing tests covering graph boundaries, failure reporting, trace protection, UI routing, and diagnostic leakage.

## What this establishes

The implementation meets the Track A collaboration, tool-use, observability, and human-checkpoint behaviors on the demonstrated cases. The evaluation does not establish an accuracy benefit from multiple agents: the baseline was faster and performed better on the frozen small set. The graph's value here is explicit control over clarification and review. In a real deployment, retain the simpler baseline unless evidence shows that the additional control is worth its latency and complexity.

Before production, use real permissioned policies, independently review evaluation labels, test contradictory versions and prompt injection, and add retrieval-time authorization and durable session state. These are limitations and future alternatives, not implemented features.
