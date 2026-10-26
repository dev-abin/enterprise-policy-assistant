"""Pause a genuine model run for an externally supplied human clarification.

Used during assisted local verification. For normal use, use Streamlit.
"""
import json
import sys
import time
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from policy_qa.service import Run
from policy_qa.llm import Ollama
from policy_qa.retrieval import PolicyIndex

run = Run(Ollama(), PolicyIndex(), prefix="demo", actor="human")
run.start("When should I submit my claim?")
print(json.dumps({"run_id": run.id, "pending": run.pending, "final": run.state.get("final")}), flush=True)
if run.pending:
    response_file = ROOT / ".runtime" / (run.id + "-reply.json")
    print("WAITING_FOR_HUMAN_FILE=" + str(response_file), flush=True)
    deadline = time.monotonic() + 1200
    while not response_file.exists() and time.monotonic() < deadline:
        time.sleep(1)
    if not response_file.exists():
        print("No reply received. Run remains uncompleted; no approval inferred.", flush=True)
        sys.exit(2)
    reply = json.loads(response_file.read_text(encoding="utf-8-sig"))
    run.resume(reply["text"])
    print(json.dumps(run.state["final"]), flush=True)
print("TRACE=" + str(run.trace.path), flush=True)
