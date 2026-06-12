# XBRL & Filing Mechanics Skill

Use this skill when the user asks about SEC filing mechanics, EDGAR readiness, exhibits, cover-page items, form requirements, or XBRL/iXBRL tagging considerations.

Workflow:
- Identify filing form, period, filer type, and requested mechanics area.
- Retrieve SEC rule/context when needed.
- Check required exhibits, cover page signals, filing dates, and operational readiness items.
- For XBRL, focus on tagging considerations, consistency, and review questions rather than pretending to validate a full taxonomy.
- Flag items needing counsel, SEC reporting owner, or filing agent confirmation.

Required inputs:
- Filing type such as Form 10-K, 10-Q, 8-K, S-1, or other.
- Draft filing package or specific mechanics question.
- Filer status when relevant.

Output style:
- Return a mechanics checklist or answer.
- Separate rules, operational steps, and open confirmations.
- Do not provide legal sign-off.

Common failure modes:
- Treating XBRL tagging as deterministic without taxonomy tooling.
- Ignoring filer status or form type.
- Mixing accounting disclosure substance with EDGAR mechanics.
