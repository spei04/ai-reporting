# Financial Statement Flux Analysis Skill

Use this skill when the user asks for balance sheet, income statement, cash-flow, or financial statement movement analysis.

Workflow:
- Identify the statement, line items, and comparison periods.
- Calculate absolute and percentage movements when data is available.
- Group drivers by source support.
- Identify likely disclosure, MD&A, or close-review implications.
- Flag movements that need management explanation.

Required inputs:
- Current and comparison financial statements or support data.
- Period basis and units.
- Materiality threshold if available.

Output style:
- Lead with largest or most material movements.
- Include table-style movement summaries when possible.
- Distinguish calculated movements from explanatory narrative.

Common failure modes:
- Explaining changes without calculating them.
- Ignoring classification or sign changes.
- Overlooking disclosure implications for large movements.
