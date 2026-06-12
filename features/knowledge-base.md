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

## Design Rule

Shared ASC/SEC rules are available to every user. Uploaded company files are private to the active session/user context.
