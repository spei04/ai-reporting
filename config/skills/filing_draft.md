# Filing Draft Skill

Use this skill when the user asks to draft, revise, or review SEC filing language, MD&A, footnotes, or disclosure text.

Workflow:
- Identify the filing type, period, company context, and section to draft.
- Retrieve relevant SEC and ASC guidance only for the filing topic.
- Use uploaded source support, approved financial statements, or generated reporting artifacts as factual inputs.
- Draft language separately from open questions and required support.
- Do not invent company facts, amounts, risk factors, or rule support.

Required inputs:
- Filing section or disclosure topic.
- Source financials, support schedule, or user-provided facts.
- Reporting period and filer context when relevant.

Output style:
- Provide draft language first when enough support exists.
- Then list support used, rule support, and open questions.
- Keep draft language clean enough to paste into a working document.

Common failure modes:
- Drafting boilerplate without source facts.
- Mixing reviewer notes into filing language.
- Citing rules that were not retrieved.
