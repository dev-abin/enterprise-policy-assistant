# Case Study Requirements

Source: `Avathon_AI_Hiring_Challenge.docx`

Selected combination: **Track A — Agentic / Multi-Agent AI** and **Scenario S2 — Gen AI for Enterprise Documents**.

## Scenario

- Address an enterprise problem involving unstructured content such as contracts, reports, SOPs, or emails.
- Support extraction, classification, summarization, or question answering. The document does not require all four capabilities.
- Clearly define the business problem and justify why agentic AI is appropriate.
- Choose exactly one track; do not combine tracks.

## Mandatory Track A Requirements

- Implement a multi-agent system in which autonomous agents collaborate to solve the chosen enterprise problem.
- Include at least **three agents** with distinct, well-defined roles.
- Demonstrate genuine role separation and observable inter-agent communication. A single LLM with a long prompt does not qualify.
- Use an orchestration framework or justify a custom orchestrator.
- Define a message schema for agent communication, documented with types and example payloads.
- Have at least one agent use an external tool, such as code execution, an API call, retrieval, or a database query.
- Include at least one human-in-the-loop checkpoint where a human can review, override, or approve before the system proceeds.
- Provide full agent interaction traces for at least **two end-to-end scenarios**:
  - A success path.
  - An edge case or failure path.

## Required Design Reasoning

Explicitly address these questions in the write-up:

- Why agentic AI instead of a simpler single-LLM pipeline or classical ML model?
- Why the selected orchestration framework over alternatives, and what trade-offs were accepted?
- How does the agent decomposition map to the problem, and why that number or grouping of agents?
- Where could the system fail silently, and how were those failures mitigated or detected?

## Data Requirements

- Source your own data; no data is provided.
- Open-source or synthetic data is acceptable.
- Document the data source and explain why it fits the scenario.
- If using synthetic data, provide the generation script, document distributions and assumptions, and acknowledge the gap to real-world data.

## Submission Requirements

### Where to Submit Each Deliverable

**Final submission destination: the submission link provided separately by your recruiter.** Submit all three items through that link:

| Deliverable | Where to host or prepare it | What to submit through the recruiter's link | Additional placement required |
|---|---|---|---|
| GitHub repository | GitHub, public or private | Repository URL | For a private repository, grant access to the reviewer's GitHub handle supplied separately by the recruiter. |
| Walkthrough video | Google Drive, Dropbox, or YouTube (unlisted) | Video URL | Also include the video URL in the repository's `README.md`. |
| Technical write-up | PDF, one to two pages, minimum 11pt font | Write-up PDF | Include your name and track letter at the top of the PDF. |

**The case study document does not contain the actual submission URL or the reviewer's GitHub handle.** Both must come from the recruiter separately. It also does not specify the submission form's fields or whether the PDF is uploaded directly or supplied through a file link; follow the recruiter-provided submission form for that detail.

### GitHub Repository

- Public or private repository. For a private repository, add the reviewer's GitHub handle supplied by the recruiter.
- README containing the problem statement, chosen domain, data source, track, setup instructions, and instructions to reproduce all results end-to-end.
- `requirements.txt` or `environment.yaml` with pinned dependency versions; include the Python version.
- Well-organized code, data or generation script, results, and write-up.
- Commit history reflecting iterative development; the document flags a single bulk commit as a concern.
- Include the walkthrough video link in the README.

### Walkthrough Video

- Screen recording with narration, **five minutes maximum**.
- Cover the problem and approach choice, key algorithm decisions and rejected alternatives, results and what did not work, and improvements with more time.
- Suggested timing: 1 minute, 2 minutes, 1.5 minutes, and 0.5 minutes respectively.
- Focus on decisions, reasoning, and trade-offs; do not narrate code line by line.
- Upload to Google Drive, Dropbox, or YouTube (unlisted).
- Put the video URL in `README.md` **and** submit it through the recruiter's submission link.

### Technical Write-Up

- **PDF, one to two pages, minimum 11pt font**.
- Include your name and track letter at the top.
- Cover four sections:
  1. **Problem and domain:** the problem, its value as an AI opportunity, and why the track fits.
  2. **Approach and algorithm decisions:** at least one considered alternative and rejection rationale for every major algorithmic choice, including the Track A reasoning questions above.
  3. **Results and error analysis:** key metrics on a held-out evaluation set, failures, and their causes.
  4. **Production and limitations:** one concrete production consideration and one limitation requiring attention before deployment.

## Timeline and Submission

- Complete within **48 hours of receiving the document**; no extensions.
- Raise requirement questions with the recruiter within the first **four hours** of receipt.
- Final submission must include **all three items** through the recruiter's submission link: **GitHub URL + video URL + write-up PDF**. The video URL must also appear in `README.md`.
- No GPU spending is required. Open-source libraries, cloud free tiers, and local compute are allowed.
- External LLM APIs are permitted for Track A. Justify tooling choices.

## Evaluation Weights

| Dimension | Weight |
|---|---:|
| Problem framing and approach rationale | 25% |
| Algorithm selection and alternative analysis | 30% |
| Technical execution and correctness | 25% |
| Results, evaluation, and honest error analysis | 10% |
| Communication and clarity | 10% |

Track A does not specify a minimum evaluation-set size, a particular metric, a particular framework, or a user interface. Its explicit demonstration minimum is the two end-to-end interaction traces above.
