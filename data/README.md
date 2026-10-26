# Synthetic policy data

Source: `scripts/generate_data.py`, authored for this assessment. The four fictional policies represent employee procedure questions. They contain 11 short sections with stable document/section IDs.

Generation is deterministic: every template is emitted once. No population sampling, randomness, or LLM synthesis is used. The script is the complete fixed value table: travel claims 30 calendar days, medical claims 60 calendar days, annual leave notice 10 working days, sick notification 10 a.m., temporary access 7 calendar days, permanent access review 90 calendar days, incident reporting 15 minutes. Roles, documents, and submission channels are also fixed in the script.

The documents are not real employer policies. They omit complex exceptions, document noise, conflicting versions, tables, and access permissions. Results cannot establish production reliability or business savings.

Development: 4 cases. Held-out evaluation: 8 cases (3 direct, 2 multi-section, 1 ambiguous, 2 unsupported). Evaluation expectations are fixed before development runs. The ambiguous case supplies only a user circumstance when clarification is requested. The graph never receives expected facts or gold source IDs. Policies are searchable knowledge, not training examples. No weights are trained.

Development and evaluation exercise different question targets; some share policy facts, so this is a question-level holdout, not a disjoint-document or disjoint-fact generalization test. This limitation is reported explicitly.
