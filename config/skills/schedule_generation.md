# Schedule Generation Skill

Use this skill when the user asks to generate a reporting support schedule such as debt, lease, depreciation, amortization, equity, tax, or rollforward support.

Workflow:
- Identify the schedule type and period.
- Collect the minimum required assumptions or source file.
- Use deterministic tools for calculations and workbook generation when available.
- Produce downloadable output only when a schedule is actually generated.
- Preserve assumptions and source references in the artifact.

Required inputs:
- Schedule type.
- Core assumptions, such as principal, rate, term, dates, useful life, or source table.
- Reporting period.

Output style:
- Ask for missing assumptions before generating.
- When generated, summarize inputs, outputs, and download artifact.
- Avoid adding unrelated accounting guidance unless the user asks for it.

Common failure modes:
- Creating a file when the user only asked a question.
- Guessing assumptions.
- Forgetting to make the schedule auditable.
