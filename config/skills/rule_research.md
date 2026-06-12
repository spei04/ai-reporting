# ASC/SEC Rule Research Skill

Use this skill when the user asks what ASC, SEC, Regulation S-X, Regulation S-K, or other reporting guidance requires.

Workflow:
- Retrieve relevant shared ASC/SEC rule context before answering.
- Answer with the rule conclusion first.
- Separate general rule requirements from company-specific facts.
- Identify missing facts when the conclusion depends on transaction details, period, filer status, or materiality.
- Cite the retrieved rule references that support the answer.

Required inputs:
- Rule topic or reporting question.
- Company-specific facts only if the user asks for a conclusion that depends on facts.

Output style:
- Keep the answer direct and practical for a reporting team.
- Avoid long legal-style exposition unless the user asks for depth.
- Do not claim paragraph-level support unless retrieved context includes paragraph-level detail.

Common failure modes:
- Treating a seed summary as full paragraph-level support.
- Giving a definitive accounting conclusion without transaction facts.
- Retrieving rules for ordinary writing or non-reporting questions.
