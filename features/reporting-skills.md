# Reporting Skills

## Purpose

Route clear reporting workflows into discrete backend skills while preserving ordinary GPT chat for uncategorized questions.

## Current Skills

| Skill | Purpose |
|---|---|
| Intake & Context | Clarify missing files, amounts, dates, and workflow scope. |
| Source File Parsing | Understand uploaded files and map them into standard reporting context. |
| SCF Generation | Generate statement-of-cash-flows outputs from support data. |
| Schedule Generation | Generate reporting workpaper schedules such as debt, lease, depreciation, and rollforward support. |
| Source Trace & Evidence | Explain where values came from and connect outputs to source support. |
| ASC/SEC Rule Research | Answer rule-backed accounting and SEC questions. |
| Filing Draft | Draft SEC filing/disclosure language from source support and rules. |
| Disclosure Checklist | Identify required disclosures, support needs, and open reporting questions. |
| Contract Accounting | Analyze contracts for accounting treatment and memo support. |
| Review & Validation | Check outputs for tie-outs, missing support, completeness, and rule coverage. |

## Routing Behavior

- The router is conservative and keyword/context based.
- If a skill matches, the selected skill context is passed into the model call.
- If no skill matches, the model call receives no skill context.
- Deterministic tools can bypass GPT when they need exact calculations or file generation.

## Currently Deterministic

- SCF generation is deterministic through `/api/generate` when a workbook is uploaded and the UI detects a cash-flow generation request.
