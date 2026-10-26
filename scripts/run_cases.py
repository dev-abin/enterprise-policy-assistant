"""Run development or frozen evaluation cases; replies are explicitly simulated."""
import argparse
import hashlib
import json
import sys
import time
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from policy_qa.llm import Ollama
from policy_qa.retrieval import PolicyIndex
from policy_qa.service import Run
from policy_qa.agents import WRITE
from policy_qa.schemas import Draft
from policy_qa.traces import Trace
import uuid


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--split", choices=["dev", "eval"], default="dev")
    parser.add_argument("--model", default="qwen3.5:4b")
    parser.add_argument("--baseline", action="store_true")
    parser.add_argument("--only")
    args = parser.parse_args()
    index, llm = PolicyIndex(), Ollama(args.model)
    fixture = ROOT / "data" / (args.split + ".jsonl")
    records = [json.loads(line) for line in fixture.read_text().splitlines()]
    if args.only:
        records = [r for r in records if r["id"] == args.only]
    stamp = time.strftime("%Y%m%d-%H%M%S")
    output = ROOT / "results" / f"{args.split}-{'baseline' if args.baseline else 'agents'}-{stamp}.json"
    results = []
    for record in records:
        started = time.perf_counter()
        result = {"id": record["id"], "question": record["question"]}
        trace = None
        try:
            if args.baseline:
                run_id = "baseline-" + uuid.uuid4().hex
                trace = Trace(ROOT / "results/traces" / (run_id + ".jsonl"), run_id)
                trace.emit("orchestrator", "orchestrator", "metadata", {"model": llm.model, "model_digest": llm.digest, "corpus_sha256": index.corpus_hash, "baseline": True})
                query = record["question"] + (" User scope: " + record["reply"] if record.get("reply") else "")
                trace.emit("user", "writer", "question", {"text": query})
                trace.emit("orchestrator", "retrieval_tool", "tool_call", {"query": query, "k": 3})
                evidence = index.search(query)
                trace.emit("retrieval_tool", "writer", "tool_result", {"evidence": evidence})
                draft = llm.structured("writer", WRITE, {"question": record["question"], "user_clarification": record.get("reply", ""), "evidence": evidence}, Draft, trace)
                final = {"status": "abstained" if draft.abstain else "answered", "answer": draft.answer, "source_ids": draft.source_ids}
                trace.emit("writer", "user", "final", final)
                result.update(final=final, evidence=evidence, clarified=False)
            else:
                run = Run(llm, index, prefix=args.split, actor="simulated_fixture")
                trace = run.trace
                run.start(record["question"])
                clarified = bool(run.pending)
                if run.pending and record.get("reply"):
                    run.resume(record["reply"])
                result.update(final=run.state.get("final"), evidence=run.state.get("evidence", []),
                              clarified=clarified, pending=run.pending)
        except Exception as error:
            result["error"] = str(error)
            if trace and args.baseline:
                trace.emit("orchestrator", "user", "error", {"message": str(error)})
        result["elapsed_seconds"] = round(time.perf_counter() - started, 2)
        result["trace"] = str(trace.path.relative_to(ROOT)) if trace else None
        result["model_calls"] = sum(e["kind"] == "model_call" for e in trace.events) if trace else 0
        results.append(result)
        output.write_text(json.dumps({"model": llm.model, "digest": llm.digest, "fixture_sha256": hashlib.sha256(fixture.read_bytes()).hexdigest(), "results": results}, indent=2), encoding="utf-8")
        print(json.dumps(result), flush=True)
    print("Saved " + str(output), flush=True)


if __name__ == "__main__":
    main()
