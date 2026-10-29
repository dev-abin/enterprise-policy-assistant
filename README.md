# Enterprise policy question answering

**Track A — Agentic / Multi-Agent AI · Scenario S2 — Enterprise Documents**

Employees ask procedural questions across company policies. Three agents retrieve evidence, draft an answer, and check its support. The assistant asks for clarification when a user detail changes the applicable policy, and declines to answer when support is insufficient.

The demonstration uses four synthetic policies covering expenses, leave, system access, and security incidents. No model training is performed. See [data documentation](data/README.md) for sources and limitations.

## Run locally

Prerequisites: Python **3.12** (tested: 3.12.10) and Ollama (tested: 0.34.4). Python dependencies are pinned in `requirements.txt`.

Start Ollama in one PowerShell terminal, unless its desktop service is already running:

```powershell
ollama serve
```

From the repository root in a second terminal:

```powershell
ollama pull qwen3.5:4b  # Only if the model is not installed
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe scripts/generate_data.py
.\.venv\Scripts\python.exe -m streamlit run app.py
```

Open [localhost:8501](http://127.0.0.1:8501). The first index creation downloads approximately 79 MB of embedding weights; later runs reuse the local cache. No external LLM API key is needed. Model tags can change; the evaluated model digest is recorded in [error analysis](results/error_analysis.md).

Try “When should I submit my travel expense claim?” For clarification, ask “When should I submit my claim?” and reply “Travel expenses.” After an answer, type the next question in the same chat input. Citations show the source file name and section title on hover. Cancel a pending clarification before switching questions.

## Tests and evaluation

```powershell
# Automated tests; no live Ollama calls
.\.venv\Scripts\python.exe -m pytest -q

# Development cases
.\.venv\Scripts\python.exe scripts/run_cases.py --split dev

# Fresh evaluation run
.\.venv\Scripts\python.exe scripts/run_cases.py --split eval

# Reproduce aggregate metrics from the saved reviewed labels
.\.venv\Scripts\python.exe scripts/summarize_results.py
```

Fresh runs save timestamped results and full JSONL traces in `results/`. Automated clarification replies are labelled simulated. Review new outputs against the policies before scoring; the scoring script aggregates saved labels and does not judge new answers.

The frozen eight-question evaluation recorded **7/8 correct responses**, with correct abstention on two unsupported questions. These results describe the earlier implementation, prompts, and execution limits; they do not measure the current revision or establish production accuracy. See [results and failure analysis](results/error_analysis.md) and [saved metrics](results/evaluation.json).

## Project guide

| Location | Contents |
|---|---|
| `app.py`, `src/policy_qa/` | Streamlit entry point, agents, graph, retrieval, model client, schemas, and traces |
| `data/` | Synthetic policies and development/evaluation fixtures |
| `scripts/` | Data generation, case execution, and score aggregation |
| `tests/` | Graph, model-wrapper, and UI checks |
| `results/` | Saved results, reviewed scores, and demonstration traces |
| [DESIGN.md](DESIGN.md) | Architecture, decisions, alternatives, message contracts, and limitations |

## Submission artifacts

- [Technical write-up (PDF)](technical_writeup.pdf)
- [Narrated walkthrough video](https://drive.google.com/file/d/1GNcFqGk4Acifvh2jIrBfz_IQhbIDLlr7/view?usp=sharing)

The prototype has no document permissions or durable session recovery; see the design for production considerations.
