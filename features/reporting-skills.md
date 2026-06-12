# Reporting Skills

## Purpose

Route clear reporting workflows into discrete backend skills while preserving ordinary GPT chat for uncategorized questions.

The skills now follow a vertical-agent cache hierarchy:

- L1 is the permanent reporting system prompt.
- L2 is a curated on-demand skill spec loaded from `config/skills`.
- L3 is retrieved ASC/SEC rule context plus private session/company upload context.

## Current Skills

| Skill | Purpose |
|---|---|
| Intake & Context | Clarify missing files, amounts, dates, and workflow scope. |
| Source File Parsing | Understand uploaded files and map them into standard reporting context. |
| SCF Generation | Generate statement-of-cash-flows outputs from support data. |
| Schedule Generation | Generate reporting workpaper schedules such as debt, lease, depreciation, and rollforward support. |
| Source Trace & Evidence | Explain where values came from and connect outputs to source support. |
| Tie-Out Review | Check whether filings, disclosures, schedules, or outputs tie to source support. |
| Variance Explanation | Explain QoQ, YoY, budget-to-actual, or forecast-to-actual movements. |
| Rule-to-Claim Coverage | Check whether claims and disclosure assertions have source and rule support. |
| ASC/SEC Rule Research | Answer rule-backed accounting and SEC questions. |
| Filing Draft | Draft SEC filing/disclosure language from source support and rules. |
| Disclosure Checklist | Identify required disclosures, support needs, and open reporting questions. |
| Disclosure Draft Redline | Rewrite or redline disclosure language while preserving source-backed facts. |
| Contract Accounting | Analyze contracts for accounting treatment and memo support. |
| Accounting Memo Draft | Draft technical accounting memos from facts, support, policy, and rules. |
| Review & Validation | Check outputs for tie-outs, missing support, completeness, and rule coverage. |
| Reviewer Findings | Produce audit-style review notes with severity, owner, source location, and recommended fix. |
| Financial Statement Flux Analysis | Analyze financial statement movements and likely disclosure implications. |
| Close Package Review | Review close packages for missing schedules, stale support, broken links, and sign-off gaps. |
| XBRL & Filing Mechanics | Handle SEC filing mechanics, exhibits, cover-page items, and XBRL considerations. |
| Controls Evidence Review | Review SOX/control evidence for completeness and support quality. |

## Routing Behavior

- The router is conservative and keyword/context based.
- If a skill matches, the selected skill context is passed into the model call.
- If a matching file exists under `config/skills/{skill_id}.md`, the full curated skill playbook is loaded into `selected_skill_spec`.
- If no skill matches, the model call receives no skill context.
- Deterministic tools can bypass GPT when they need exact calculations or file generation.
- Rule retrieval is skill-aware: the backend expands the retrieval query with workflow-specific accounting/SEC hints and a short preview of the selected skill spec.
- Disclosure completeness requests bypass GPT and run the deterministic checklist engine when the user asks whether uploaded disclosures are included, missing, correct, or complete.

## L2 Skill Specs

The current curated specs are:

| Spec File | Use |
|---|---|
| `config/skills/intake_context.md` | Start workflows and ask only for missing inputs. |
| `config/skills/source_file_parsing.md` | Summarize and standardize uploaded support. |
| `config/skills/scf_generation.md` | Generate SCF summary, detailed bridge, and evidence links. |
| `config/skills/schedule_generation.md` | Generate auditable reporting schedules only when needed. |
| `config/skills/source_trace_evidence.md` | Explain output values from source support and rules. |
| `config/skills/tie_out_review.md` | Check whether outputs tie to source support. |
| `config/skills/variance_explanation.md` | Explain period-over-period or budget movements. |
| `config/skills/rule_to_claim_coverage.md` | Map claims to source evidence and rule support. |
| `config/skills/rule_research.md` | Answer ASC/SEC questions with retrieved rule support. |
| `config/skills/filing_draft.md` | Draft SEC filing language from source support and rules. |
| `config/skills/disclosure_checklist.md` | Build practical disclosure support checklists. |
| `config/skills/disclosure_draft_redline.md` | Redline disclosures without introducing unsupported facts. |
| `config/skills/contract_accounting.md` | Analyze contract facts and missing accounting inputs. |
| `config/skills/accounting_memo_draft.md` | Draft technical accounting memos. |
| `config/skills/review_validation.md` | Review generated outputs for tie-outs and support gaps. |
| `config/skills/reviewer_findings.md` | Produce severity-ranked review findings. |
| `config/skills/financial_statement_flux_analysis.md` | Analyze financial statement movement drivers. |
| `config/skills/close_package_review.md` | Review close package completeness and readiness. |
| `config/skills/xbrl_filing_mechanics.md` | Check SEC filing mechanics and XBRL considerations. |
| `config/skills/controls_evidence_review.md` | Review SOX/control evidence quality. |

## Currently Deterministic

- SCF generation is deterministic through `/api/generate` when a workbook is uploaded and the UI detects a cash-flow generation request.
- Disclosure completeness review is deterministic through chat when uploaded disclosure text is available. It returns item-level statuses and a JSON review artifact.

## Layering Impact

- L1 now includes deterministic reporting primitives, not just prompt behavior. Disclosure completeness becomes a common operation the backend can execute reliably.
- L2 still owns the workflow playbook: when to run the checker, what facts are needed, and how to interpret results.
- L3 remains the raw substrate: uploaded disclosure documents, private session context, and shared ASC/SEC rule context.
