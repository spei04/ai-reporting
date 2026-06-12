# Reviewer Findings Skill

Use this skill when the user asks for review notes, audit-style findings, open items, or comments on a schedule, disclosure, filing, or generated output.

Workflow:
- Inspect the target document or artifact.
- Identify findings by severity: must fix, needs review, informational, clean.
- Include source location, owner or likely owner when clear, and recommended fix.
- Separate mechanical defects from accounting judgment items.
- Avoid duplicating the same finding across multiple rows unless each instance matters.

Required inputs:
- Document, schedule, output artifact, or uploaded support.
- Review objective and materiality threshold if applicable.

Output style:
- Lead with findings, ordered by severity.
- Use concise reviewer language.
- Include next action for each finding.

Common failure modes:
- Returning generic advice instead of actionable findings.
- Omitting source locations.
- Labeling judgmental items as errors.
