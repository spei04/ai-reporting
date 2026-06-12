# Rule-to-Claim Coverage Skill

Use this skill when the user asks whether every claim, sentence, amount, or disclosure assertion is backed by source evidence and accounting/SEC rule support.

Workflow:
- Break the target text into discrete claims.
- Classify each claim as factual, numerical, accounting conclusion, SEC disclosure assertion, or drafting language.
- Map factual and numerical claims to uploaded source support.
- Map accounting and SEC claims to retrieved ASC/SEC guidance.
- Flag unsupported, partially supported, and ambiguous claims.

Required inputs:
- Disclosure, memo, filing excerpt, or draft language.
- Source support and relevant rule context when available.

Output style:
- Return a claim coverage table.
- Include claim, support status, source support, rule support, and recommended fix.
- Do not rewrite unsupported claims unless the user asks.

Common failure modes:
- Treating a citation near a paragraph as support for every sentence.
- Missing implied claims embedded in adjectives such as material, significant, or primarily.
- Citing rules without tying them to the specific claim.
