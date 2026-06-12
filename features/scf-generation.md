# SCF Generation

## Purpose

Generate a standardized cash-flow statement package from uploaded support data.

## Current Features

- Parses uploaded `.xlsx` support workbooks.
- Uses workbook profiling to tolerate sheet-name variation.
- Uses learned source-cell mapping for selected moved rows/columns.
- Uses reviewer-approved parser overrides from `config/company_parser_profile.json`.
- Generates:
  - `1. SCF`
  - `2. 26Q1 QTD`
  - `2a. 2026 YTD`
- Outputs:
  - generated SCF workbook
  - generated values JSON
  - evidence links JSON
  - normalized support JSON
  - workbook profile JSON
  - mapping review JSON
- Adds an `Evidence Index` sheet to generated workbooks.
- Adds hyperlinks/comments from evidenced generated cells to the evidence index.
- Evidence JSON includes output value, output formula, dependency details, source locations, rule reference, and review status for inspector views.
- The chat interface can inspect SCF evidence for generated output cells without opening raw JSON.

## Validation

The development-only `answer.xlsx` file is used only after generation to validate the engine. It is not a production input and is not read during generation.
