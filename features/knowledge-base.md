# Knowledge Base

## Purpose

Give the assistant permanent reporting knowledge plus user/session-specific private context.

## Current Features

- Shared static knowledge database at `data/reporting_knowledge.db`.
- Static corpus includes ASC and SEC rule documents from `data/raw`.
- Separate global tables:
  - `global_documents`
  - `global_rule_chunks`
  - `global_rule_edges`
- Separate user-private tables:
  - `user_documents`
  - `user_document_chunks`
  - `user_document_edges`
- Uploaded files are summarized and indexed into private session-scoped knowledge.
- Chat requests retrieve:
  - global ASC/SEC rule context
  - user/session upload context
  - recent session message context
- Rule retrieval is gated by the selected reporting skill. Generic chat does not retrieve ASC/SEC context by default.
- Skill-aware retrieval expands queries with workflow-specific hints, such as ASC 230 for SCF generation and Regulation S-X/S-K for filing drafts.

## Design Rule

Shared ASC/SEC rules are available to every user. Uploaded company files are private to the active session/user context.

## Vertical Agent Role

The knowledge base is the L3 escape hatch in the reporting agent architecture. The permanent prompt and curated skill specs should stay compact; raw ASC/SEC and user documents are retrieved only when the routed workflow needs them.
