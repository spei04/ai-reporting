# AI Reporting Integrations Roadmap

## Implemented First: Slack

Slack is the first external interface for the reporting agent.

### Current Slack capabilities

- `GET /api/slack/install`
  - Creates a Slack OAuth install URL using `SLACK_CLIENT_ID`, `SLACK_SCOPES`, and the configured redirect URI.
- `GET /api/slack/oauth/callback`
  - Exchanges the Slack OAuth code for a workspace bot token using `oauth.v2.access`.
  - Stores installations in `data/slack/installations.json`.
  - Optionally restricts installs with `SLACK_ALLOWED_TEAM_IDS`.
- `POST /slack/commands`
  - Handles the `/reporting` slash command.
  - Verifies Slack request signatures with `SLACK_SIGNING_SECRET`.
  - Maps each Slack user/channel/workspace to a persistent reporting session.
  - Acknowledges Slack immediately and responds asynchronously through `response_url`.
- `POST /slack/events`
  - Handles Slack Events API URL verification.
  - Handles app mentions and direct-message events.
  - Downloads Slack file attachments when a bot token is available, stores them as private session context, and routes the question through the reporting agent.
- Session mapping
  - Slack session IDs use the shape `slack_{team_id}_{channel_id}_{user_id}`.
  - This allows future Slack questions from the same context to reference prior uploads and answers.

### Slack app configuration

Create a Slack app and configure:

- Slash command: `/reporting`
  - Request URL: `https://your-domain/api/slack/commands`
- Event subscriptions:
  - Request URL: `https://your-domain/api/slack/events`
  - Bot events:
    - `app_mention`
    - `message.im`
- OAuth redirect URL:
  - `https://your-domain/api/slack/oauth/callback`
- Bot token scopes:
  - `commands`
  - `chat:write`
  - `app_mentions:read`
  - `im:history`
  - `im:read`
  - `im:write`
  - `files:read`

For local development, expose the local server through an HTTPS tunnel and set:

```text
AI_REPORTING_PUBLIC_BASE_URL=https://your-tunnel.example.com
SLACK_REDIRECT_URI=https://your-tunnel.example.com/api/slack/oauth/callback
```

## Feature Plan For Additional Integrations

### 1. Slack interactive approvals

Goal: make Slack safe for controlled reporting workflows.

- Add Block Kit buttons for:
  - Approve draft
  - Request changes
  - Download workbook
  - Open source trace
- Add `POST /slack/interactions`.
- Store approval state in the session manifest.
- Require approval before any write-back to filing, ticketing, ERP, or document systems.

### 2. Company file systems

Goal: let users ask questions over company support files without manually uploading everything.

Priority connectors:

- Google Drive
- SharePoint / OneDrive
- Box

Implementation:

- OAuth per customer/user.
- Connector tables for linked accounts, source documents, permissions, sync state, and document chunks.
- Scheduled indexing jobs for approved folders.
- Respect source ACLs when retrieving context.

### 3. ERP and accounting systems

Goal: pull controlled financial data into reporting workpapers.

Priority connectors:

- NetSuite
- SAP
- Oracle ERP
- Workday Financials
- QuickBooks for smaller customers

Implementation:

- Start read-only.
- Create tools such as `query_trial_balance`, `fetch_gl_detail`, `fetch_subledger_activity`, and `get_entity_mapping`.
- Store all query inputs, result hashes, timestamps, and user IDs for audit.
- Require explicit approval before posting journals or changing source systems.

### 4. Data warehouse connectors

Goal: support companies whose reporting data already lands in warehouse tables.

Priority connectors:

- Snowflake
- BigQuery
- Redshift
- Databricks SQL

Implementation:

- Read-only service account or delegated user OAuth.
- Whitelisted semantic queries instead of arbitrary SQL at first.
- Query result caching by hash.
- Evidence links back to query text, result set, warehouse, schema, and run timestamp.

### 5. Filing and disclosure tools

Goal: push prepared drafts into the systems reporting teams already use.

Priority connectors:

- Workiva
- ActiveDisclosure
- Donnelley / filing provider exports
- Microsoft Word / SharePoint document workflows

Implementation:

- Generate drafts locally first.
- Add export adapters by target system.
- Preserve rule citations and source trace IDs as comments or embedded metadata.
- Add reviewer approval workflow before publishing.

### 6. Contract and revenue systems

Goal: support booking memo and revenue analysis workflows.

Priority connectors:

- Salesforce
- Ironclad
- DocuSign CLM
- Conga
- Order management systems

Implementation:

- Ingest contracts and order forms.
- Extract performance obligations, renewal terms, cancellation clauses, pricing, and billing schedules.
- Retrieve ASC 606 rule context.
- Generate booking memo drafts with source clause links.

### 7. Ticketing and review workflow

Goal: move exceptions into the customer’s existing close process.

Priority connectors:

- Jira
- Asana
- Linear
- ServiceNow

Implementation:

- Create tickets for missing support, mapping exceptions, and review comments.
- Sync status back into the reporting session.
- Link each ticket to the relevant output value, source file, and rule citation.

### 8. MCP connector layer

Goal: avoid custom one-off integrations forever.

- Wrap each connector behind a small tool contract.
- Expose tools through MCP where possible.
- Keep the reporting agent’s core orchestration independent from individual vendor APIs.
- Add allowlists, per-tool permissions, logging, and approval gates.

## Security Requirements Across All Integrations

- Verify inbound webhook signatures.
- Encrypt stored tokens.
- Keep customer data separated by tenant and user.
- Apply source permissions during retrieval.
- Log every external read and write.
- Prefer read-only scopes until a workflow needs write access.
- Require human approval for external side effects.
- Keep generated outputs traceable to source documents, rule context, user action, and model response metadata.
