# Technical Architecture Plan

## North Star

The product should become a trusted operating layer for financial reporting teams.

Design principles:

- The model reasons, drafts, classifies, and explains.
- Deterministic services own calculations, validations, document generation, approval state, and evidence.
- Every material answer should be reconstructable from source context, retrieved chunks, tool inputs, model call metadata, and generated artifacts.
- Agents should only act through governed tools with permissions, audit logs, and human approval where needed.

## Phase 1 Architecture

Keep the current modular monolith until there is real operational pressure to split services.

```text
Web Chat UI
Slack App
    |
Python Backend API
    |
    |-- Auth / Tenant / Session Layer
    |-- Reporting Agent Orchestrator
    |-- Retrieval Service
    |-- Tool Registry
    |-- Upload / File Processing
    |-- Evidence / Citation Service
    |-- Audit Logger
    |
Data Layer
    |-- SQLite locally, Postgres in production
    |-- Vector Index
    |-- Object/File Store
    |-- Job Queue
    |
Integrations
    |-- Slack
    |-- Workiva
    |-- ERP
    |-- Docs / Drive / SharePoint
    |-- Historical Reporting Packages
```

## Core Data Model

Move toward a tenant-first schema. Every durable object should be scoped by `tenant_id`.

Core entities:

- `tenants`
- `users`
- `sessions`
- `messages`
- `documents`
- `document_versions`
- `document_chunks`
- `citations`
- `knowledge_sources`
- `reporting_tasks`
- `artifacts`
- `tool_runs`
- `agent_runs`
- `audit_events`
- `integration_connections`
- `integration_sync_jobs`

Store the exact context needed to reconstruct the output:

- User question.
- Prompt version.
- Retrieved source IDs.
- Source excerpts.
- Tool calls.
- Tool outputs.
- Model response.
- Generated artifacts.
- Validation status.
- Human review status.

## Knowledge And Retrieval

Use layered context:

1. Global authoritative knowledge.
   ASC, SEC rules, public reporting guidance, and shared templates.

2. Tenant institutional knowledge.
   Company policies, memos, prior filings, historical packages, auditor comments, disclosure checklists, and reporting calendars.

3. Session-private knowledge.
   User uploads, temporary files, drafts, and ad hoc analysis.

Retrieval should evolve to hybrid search:

- Keyword/BM25 for exact rule references, account names, filing terms, and section numbers.
- Vector search for semantic questions.
- Metadata filters for tenant, user permission, period, entity, source type, document version, and confidentiality.
- Reranking before generation.
- Citation validation after generation.

Start with a thin reporting graph:

- `Document -> Period`
- `Document -> Entity`
- `Document -> Reporting Area`
- `Policy -> Applies To -> Account / Disclosure`
- `Memo -> Supports -> Judgment`
- `Workbook Cell -> Supports -> Financial Statement Line`
- `Guidance Section -> Cited By -> Answer / Memo / Task`
- `Prior Filing -> Contains -> Disclosure`

## Agent Orchestration

Upgrade the current skill router into a governed planner/executor.

Modes:

- Answer mode: cited reporting answers.
- Analysis mode: uploaded support analysis and deterministic tools.
- Workflow mode: multi-step reporting tasks with artifacts and review state.
- Clarification mode: ask for missing period, entity, workbook, filing section, or source.

Flow:

```text
Router
  -> Intent Classifier
  -> Retrieval Planner
  -> Tool Selector
  -> Deterministic Tool Execution
  -> Evidence Compiler
  -> Response Generator
  -> Validation / Citation Check
```

Initial specialized agents:

- Guidance research agent.
- Disclosure drafting agent.
- SCF support agent.
- Tie-out/reconciliation agent.
- Policy lookup agent.
- Historical package comparison agent.

Each agent needs:

- Input schema.
- Permitted tools.
- Output schema.
- Required citations.
- Validation checks.
- Audit event trail.

## Deterministic Engines

The SCF engine is the pattern to expand.

Good deterministic candidates:

- Cash flow support.
- Disclosure tie-outs.
- Rollforward validation.
- Flux analysis.
- Trial balance mapping.
- Footnote number tie-outs.
- Workbook formula/source validation.
- XBRL/filing consistency checks.

The model should not be the calculator of record.

## Security And Auditability

Minimum viable enterprise posture:

- Tenant isolation.
- Role-based access control.
- Document-level ACLs where source systems support them.
- Encryption at rest for files and secrets.
- Secret storage outside the app database.
- Audit trail for user actions, model calls, tool runs, file access, retrieval, and artifact generation.
- No cross-tenant retrieval.
- Data retention controls.
- Admin controls for uploaded and promoted knowledge.
- Human approval gates for external side effects.

Every material answer should preserve an internal evidence trace:

- Question.
- Prompt version.
- Retrieved sources.
- Source excerpts.
- Tool calls and outputs.
- Model response.
- Citations.
- Assumptions.
- Validation status.
- Human review status.

Response labels:

- `Cited`
- `Partially cited`
- `Needs review`
- `No authoritative source found`
- `Calculated by deterministic engine`

## Engineering Milestones

### Milestone 1: Production Foundation

- Add tenant-aware schema.
- Add durable documents, chunks, citations, artifacts, tool runs, agent runs, and audit events.
- Make uploads metadata-driven.
- Add retrieval permission filters.
- Add structured citation objects to answers.

### Milestone 2: Retrieval Quality And Evidence

- Implement hybrid retrieval and reranking.
- Normalize source metadata.
- Add answer citation validation.
- Add no-source-found behavior.
- Preserve internal evidence traces for sourced answers.
- Reserve downloadable evidence artifacts for workflows that generate files or explicit export requests.

### Milestone 3: SCF Workflow Productization

- Store source workbook, generated workbook, validation report, and evidence artifacts.
- Add user-facing workflow state.
- Add downloadable audit bundle.
- Add tests with known-answer workbooks.

### Milestone 4: Integration MVP

- Build connector abstraction.
- Add one document source integration.
- Add one financial-data integration.
- Preserve source URLs and permissions.
- Add sync job observability.

### Milestone 5: Orchestration Upgrade

- Replace loose routing with structured modes.
- Add tool registry.
- Add output schemas per agent.
- Add clarification behavior.
- Add routing evaluation suite.

### Milestone 6: Institutional Memory

- Allow users to promote files and answers to tenant knowledge.
- Add period/entity/account metadata.
- Add approved memo/policy memory.
- Add prior-answer and prior-artifact retrieval.
