"""Run development or frozen evaluation cases; replies are explicitly simulated."""

import argparse
import hashlib
import json
import logging
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from policy_qa.llm import Ollama
from policy_qa.retrieval import PolicyIndex
from policy_qa.service import Run

logger = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--split", choices=["dev", "eval"], default="dev")
    parser.add_argument("--model", default="qwen3.5:4b")
    parser.add_argument("--only")
    args = parser.parse_args()
    index, llm = PolicyIndex(), Ollama(args.model)
    fixture = ROOT / "data" / (args.split + ".jsonl")
    records = [json.loads(line) for line in fixture.read_text().splitlines()]
    if args.only:
        records = [r for r in records if r["id"] == args.only]
    stamp = time.strftime("%Y%m%d-%H%M%S")
    output = ROOT / "results" / f"{args.split}-agents-{stamp}.json"
    results = []
    for record in records:
        started = time.perf_counter()
        result = {"id": record["id"], "question": record["question"]}
        trace = None
        try:
            run = Run(llm, index, prefix=args.split, actor="simulated_fixture")
            trace = run.trace
            run.start(record["question"])
            clarified = bool(run.pending)
            if run.pending and record.get("reply"):
                run.resume(record["reply"])
            result.update(
                final=run.state.get("final"),
                evidence=run.state.get("evidence", []),
                clarified=clarified,
                pending=run.pending,
            )
        except Exception as error:
            logger.exception("Evaluation case %s failed", record["id"])
            result["error"] = str(error)
        result["elapsed_seconds"] = round(time.perf_counter() - started, 2)
        result["trace"] = str(trace.path.relative_to(ROOT)) if trace else None
        result["model_calls"] = (
            sum(e["kind"] == "model_call" for e in trace.events) if trace else 0
        )
        results.append(result)
        output.write_text(
            json.dumps(
                {
                    "model": llm.model,
                    "digest": llm.digest,
                    "fixture_sha256": hashlib.sha256(fixture.read_bytes()).hexdigest(),
                    "results": results,
                },
                indent=2,
            ),
            encoding="utf-8",
        )
        print(json.dumps(result), flush=True)
    print("Saved " + str(output), flush=True)


if __name__ == "__main__":
    main()
