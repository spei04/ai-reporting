# Contract Accounting Skill

Use this skill when the user asks to analyze a contract, draft a booking memo, identify journal-entry implications, or assess revenue, lease, derivative, or other accounting treatment.

Workflow:
- Extract contract facts from uploaded documents or user-provided terms.
- Identify missing terms that affect accounting treatment.
- Retrieve relevant ASC guidance based on the contract topic.
- Separate factual extraction, accounting analysis, proposed booking view, and open questions.
- Do not assume terms not present in the source.

Required inputs:
- Contract or clear contract fact pattern.
- Reporting period and company policy context when available.

Output style:
- Start with the likely accounting path only if support is sufficient.
- Include missing terms before making a definitive conclusion.
- Provide journal-entry implications only when amounts and timing are available.

Common failure modes:
- Drafting a memo from incomplete contract facts.
- Treating commercial intent as accounting evidence.
- Forgetting to cite ASC guidance for recognition or classification conclusions.
