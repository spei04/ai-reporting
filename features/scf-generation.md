# SCF Generation

## Purpose

Generate a standardized cash-flow statement package from uploaded support data.

## Current Features

- Parses uploaded `.xlsx` support workbooks.
- Uses the curated L2 playbook at `config/skills/scf_generation.md` when chat routes a request into SCF generation.
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
- Evidence linking follows generated-cell dependency chains, so subtotal outputs can still be marked linked when their underlying generated rows trace back to source support.
- The chat interface can inspect SCF evidence for generated output cells without opening raw JSON.
- Chat retrieval for SCF requests is expanded with ASC 230 and cash-flow presentation hints before querying the shared rule knowledge base.

## Validation

The development-only `answer.xlsx` file is used only after generation to validate the engine. It is not a production input and is not read during generation.

## Vertical Agent Requirements

- The engine should ask for missing support instead of generating unsupported cash-flow outputs.
- The engine should preserve QTD vs YTD period context and should not create future quarter columns when only Q1 data exists.
- The engine should report mapped, unmapped, and review-needed lines after generation.
- Output values should remain clickable or traceable back to support data.
