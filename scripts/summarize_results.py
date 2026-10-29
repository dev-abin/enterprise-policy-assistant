"""Aggregate explicitly reviewed labels; this is not an automatic semantic judge."""

import json
import statistics
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
review = json.loads((ROOT / "results/reviewed_scores.json").read_text())
output = {
    "reviewer": review["reviewer"],
    "metric_definition": review["metric_definition"],
    "implementation_commit": "1c0adf84e52e581e5f17193f608f1cbde8641e30",
    "systems": {},
}
run = json.loads((ROOT / "results" / review["agents_file"]).read_text())
rows = run["results"]
assert [r["id"] for r in rows] == [r["id"] for r in review["records"]]
scores = [r["agents"] for r in review["records"]]
supported = sum(len(r["supported_claims"]) for r in scores)
unsupported = sum(len(r["unsupported_claims"]) for r in scores)
correct = sum(r["correct"] for r in scores)
output["systems"]["agents"] = {
    "source_file": review["agents_file"],
    "model": run["model"],
    "model_digest": run["digest"],
    "fixture_sha256": run["fixture_sha256"],
    "correct": correct,
    "total": len(rows),
    "accuracy": correct / len(rows),
    "supported_policy_claims": supported,
    "total_policy_claims": supported + unsupported,
    "citation_support": supported / (supported + unsupported),
    "correct_abstentions": sum(
        r["final"]["status"] == "abstained"
        for r in rows
        if r["id"] in ("eval-07", "eval-08")
    ),
    "unanswerable_cases": 2,
    "unnecessary_abstentions": sum(
        r["final"]["status"] == "abstained"
        for r in rows
        if r["id"] not in ("eval-07", "eval-08")
    ),
    "mean_seconds": round(statistics.mean(r["elapsed_seconds"] for r in rows), 2),
    "median_seconds": round(statistics.median(r["elapsed_seconds"] for r in rows), 2),
    "model_calls": sum(r["model_calls"] for r in rows),
    "clarification_exercised": next(
        r["clarified"] for r in rows if r["id"] == "eval-06"
    ),
}
(ROOT / "results/evaluation.json").write_text(
    json.dumps(output, indent=2) + "\n", encoding="utf-8"
)
print(json.dumps(output, indent=2))
