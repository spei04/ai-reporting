# SCF Generation Skill

Use this skill when the user asks to draft, generate, review, or explain a statement of cash flows or detailed cash flow bridge.

Workflow:
- Confirm the reporting period and whether the request is QTD, YTD, or annual.
- Parse uploaded support into the standardized SCF support template.
- Generate both SCF summary and detailed bridge when sufficient support exists.
- Maintain source links from each output amount to support rows, sheets, formulas, and files.
- Validate generated output against the development answer workbook only in test mode; never use it as runtime source truth.
- Surface mapped, unmapped, and review-needed lines.

Required inputs:
- Support workbook or standardized support data.
- Reporting period and entity scope.
- Beginning and ending cash support when available.

Rule context:
- Retrieve ASC 230 for classification, presentation, noncash activity, and reconciliation questions.
- Retrieve SEC presentation rules only when filing presentation or disclosure is requested.

Output style:
- State whether generation is ready or what support is missing.
- When generating files, include workbook artifacts and a concise work performed summary.
- When explaining values, prioritize evidence links over general accounting explanation.

Common failure modes:
- Creating Q2/Q3/Q4 columns when only Q1 data exists.
- Confusing QTD with YTD.
- Dropping sign convention issues.
- Producing values without source traceability.
