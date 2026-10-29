"""Generate fixed synthetic policies and frozen QA fixtures; no random sampling."""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
POLICIES = {
    "expenses": [
        (
            "travel-deadline",
            "Travel expense claims",
            "Employees must submit travel expense claims within 30 calendar days after returning from the trip.",
        ),
        (
            "travel-evidence",
            "Travel receipts and approval",
            "Every travel expense claim requires itemized receipts. The employee's line manager approves the claim before Finance processes payment.",
        ),
        (
            "medical-deadline",
            "Medical reimbursement claims",
            "Employees must submit medical reimbursement claims within 60 calendar days after treatment.",
        ),
        (
            "medical-evidence",
            "Medical claim documents",
            "Medical reimbursement claims require the hospital invoice and proof of payment. Submit both documents to the Benefits team.",
        ),
    ],
    "leave": [
        (
            "annual-notice",
            "Annual leave requests",
            "Submit annual leave requests in the leave portal at least 10 working days before the first day of leave.",
        ),
        (
            "sick-notice",
            "Sick leave notification",
            "Notify the line manager of sick leave before 10:00 a.m. on the first day of absence.",
        ),
    ],
    "access": [
        (
            "approval",
            "System access approval",
            "All system access requests require approval from the system owner. Submit the request through the IT service portal.",
        ),
        (
            "temporary-duration",
            "Temporary system access",
            "Temporary system access expires after 7 calendar days. Renewal requires a new request and system owner approval.",
        ),
        (
            "permanent-review",
            "Permanent system access",
            "Permanent system access is reviewed every 90 calendar days. It does not have a fixed automatic expiry date under this policy.",
        ),
    ],
    "incidents": [
        (
            "reporting",
            "Security incident reporting",
            "Report a suspected security incident to the Security Operations team within 15 minutes of discovery using the incident portal.",
        ),
        (
            "closure",
            "Security incident closure",
            "Only the Security Operations lead may close a security incident, after recording containment evidence and a root-cause summary.",
        ),
    ],
}

DEV = [
    {
        "id": "dev-direct",
        "question": "When must I submit my travel expense claim?",
        "facts": ["30 calendar days after returning"],
        "sources": ["expenses/travel-deadline"],
    },
    {
        "id": "dev-clarify",
        "question": "When should I submit my claim?",
        "reply": "A travel expense claim.",
        "facts": ["30 calendar days after returning"],
        "sources": ["expenses/travel-deadline"],
    },
    {
        "id": "dev-missing",
        "question": "What is the monthly parking reimbursement limit?",
        "abstain": True,
        "facts": [],
        "sources": [],
    },
    {
        "id": "dev-contact",
        "question": "Which team receives a suspected security incident report?",
        "facts": ["Security Operations team"],
        "sources": ["incidents/reporting"],
    },
]
EVAL = [
    {
        "id": "eval-01",
        "category": "direct",
        "question": "Which documents do I need for medical reimbursement, and where do I submit them?",
        "facts": ["hospital invoice", "proof of payment", "Benefits team"],
        "sources": ["expenses/medical-evidence"],
    },
    {
        "id": "eval-02",
        "category": "direct",
        "question": "How much notice is required for annual leave and which channel should I use?",
        "facts": ["at least 10 working days before leave", "leave portal"],
        "sources": ["leave/annual-notice"],
    },
    {
        "id": "eval-03",
        "category": "direct",
        "question": "Who must approve system access and where do I request it?",
        "facts": ["system owner", "IT service portal"],
        "sources": ["access/approval"],
    },
    {
        "id": "eval-04",
        "category": "multi",
        "question": "For travel reimbursement, when must I claim, what evidence is needed, and who approves it?",
        "facts": [
            "30 calendar days after returning",
            "itemized receipts",
            "line manager",
        ],
        "sources": ["expenses/travel-deadline", "expenses/travel-evidence"],
    },
    {
        "id": "eval-05",
        "category": "multi",
        "question": "How quickly must I report a suspected security incident, and who can close it with what evidence?",
        "facts": [
            "within 15 minutes of discovery",
            "Security Operations lead",
            "containment evidence",
            "root-cause summary",
        ],
        "sources": ["incidents/reporting", "incidents/closure"],
    },
    {
        "id": "eval-06",
        "category": "ambiguous",
        "question": "How long does my system access last?",
        "reply": "It is temporary system access.",
        "facts": ["expires after 7 calendar days"],
        "sources": ["access/temporary-duration"],
    },
    {
        "id": "eval-07",
        "category": "missing",
        "question": "What annual bonus percentage am I entitled to?",
        "abstain": True,
        "facts": [],
        "sources": [],
    },
    {
        "id": "eval-08",
        "category": "missing",
        "question": "What is the daily meal allowance amount for international travel?",
        "abstain": True,
        "facts": [],
        "sources": [],
    },
]


def main():
    folder = ROOT / "data" / "policies"
    folder.mkdir(parents=True, exist_ok=True)
    for name, sections in POLICIES.items():
        text = f"# Synthetic company {name} policy\n\n"
        text += "\n\n".join(
            f"## {key} | {title}\n{body}" for key, title, body in sections
        )
        (folder / f"{name}.txt").write_text(text + "\n", encoding="utf-8")
    for name, records in (("dev", DEV), ("eval", EVAL)):
        (ROOT / "data" / f"{name}.jsonl").write_text(
            "".join(json.dumps(r) + "\n" for r in records), encoding="utf-8"
        )
    print("Generated 4 policies, 11 sections, 4 development and 8 evaluation cases.")


if __name__ == "__main__":
    main()
