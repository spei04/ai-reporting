# Disclosure Draft Redline Skill

Use this skill when the user asks to edit, redline, rewrite, or improve filing/disclosure language.

Workflow:
- Preserve source-backed facts, amounts, period references, and rule-supported conclusions.
- Improve clarity, concision, grammar, and filing tone.
- Separate revised draft language from reviewer notes.
- Flag language that needs source support instead of inventing support.
- Keep rule references only when they are relevant to the disclosure assertion.

Required inputs:
- Draft disclosure text.
- Source support or user facts for factual changes.
- Filing type or section if tone/format matters.

Output style:
- Provide revised text first.
- Then list material edits and unsupported items.
- Avoid markdown-heavy redlines unless the user asks for marked changes.

Common failure modes:
- Changing meaning while improving grammar.
- Adding unsupported qualifiers such as material, significant, or primarily.
- Mixing reviewer notes into filing-ready text.
