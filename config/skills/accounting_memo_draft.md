# Accounting Memo Draft Skill

Use this skill when the user asks to draft a technical accounting memo, position paper, or accounting conclusion.

Workflow:
- Extract known facts and identify missing facts.
- Define the accounting issue and scope.
- Retrieve relevant ASC/SEC guidance.
- Structure the memo with facts, issue, guidance, analysis, conclusion, entries/impact, and open questions.
- Distinguish company policy from authoritative guidance.

Required inputs:
- Transaction facts or uploaded contract/support.
- Reporting period and entity context.
- Desired memo topic and conclusion scope.

Output style:
- If facts are incomplete, provide a memo skeleton and missing-input list.
- If facts are sufficient, draft memo sections clearly.
- Keep conclusion language appropriately caveated.

Common failure modes:
- Assuming missing transaction terms.
- Treating a business preference as an accounting conclusion.
- Drafting final memo language without cited guidance.
