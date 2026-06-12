# Source Trace & Evidence Skill

Use this skill when the user asks where a number came from, whether an output is supported, or why a value changed.

Workflow:
- Identify the exact value, row, period, and artifact being inspected.
- Retrieve source map, generated workbook metadata, and relevant uploaded source context.
- Explain source lineage from output value back to workbook, sheet, row/column, formula, or uploaded document.
- Distinguish source support from accounting rule support.
- Flag missing or weak support clearly.

Required inputs:
- Target number, row, file, or artifact.
- Source map or generated artifact if the value came from an engine output.

Output style:
- Start with the source answer.
- Then provide calculation path, source location, and any rule support.
- If the target value is ambiguous, ask the user which value to inspect.

Common failure modes:
- Answering with rule guidance when the user asked for source evidence.
- Citing a source file without identifying the row, sheet, or field.
- Hiding unmapped or manually entered values.
