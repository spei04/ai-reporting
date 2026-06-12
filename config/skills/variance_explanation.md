# Variance Explanation Skill

Use this skill when the user asks why balances, financial statement lines, cash-flow lines, KPIs, or disclosures changed between periods or versus budget/forecast.

Workflow:
- Identify the comparison basis: QoQ, YoY, YTD, budget-to-actual, forecast-to-actual, or other.
- Quantify the movement before explaining it.
- Retrieve uploaded support and prior session context for drivers.
- Distinguish supported drivers from plausible but unsupported explanations.
- Flag items needing management input.

Required inputs:
- Current and comparison periods.
- Source financials, support schedule, or uploaded dataset.
- Materiality or threshold if the user has one.

Output style:
- Start with the largest drivers.
- Use concise finance-language explanations suitable for reporting review.
- Mark unsupported explanations clearly.

Common failure modes:
- Producing generic explanations without source support.
- Confusing QTD, YTD, and annual changes.
- Ignoring sign conventions.
