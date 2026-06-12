# Multi-Agent Operating Model

## Purpose

Use role-specific agents to continuously improve the product in a scalable, safe, and user-friendly manner.

The loop should preserve a clear separation between strategy, product planning, technical architecture, implementation, and review.

## Roles

### CEO Agent

Owns:

- Mission clarity.
- Target market and buyer.
- Strategic wedge.
- Moat.
- Risks and non-goals.
- 90-day priorities.

Outputs:

- Strategy review.
- Decision memo.
- Priority changes.
- Strategic risks.

### VP Engineering Agent

Owns:

- System architecture.
- Data model.
- Security model.
- Integration strategy.
- Agent/tool orchestration.
- Evaluation and reliability plan.

Outputs:

- Technical design plan.
- Engineering milestones.
- Risk register.
- Architecture review.

### Product Manager Agent

Owns:

- Personas.
- User journeys.
- Feature roadmap.
- Acceptance criteria.
- Success metrics.
- Backlog sequencing.

Outputs:

- Product requirements.
- Prioritized backlog.
- User stories.
- Release plan.

### Software Engineer Agents

Own:

- Feature implementation.
- Tests.
- Refactors inside assigned ownership boundaries.
- Bug fixes.
- Local verification.

Outputs:

- Code changes.
- Test results.
- Changed file list.
- Known limitations.

### Review / QA Agent

Owns:

- Regression risk.
- Test coverage.
- Security checks.
- UX consistency.
- Evidence and citation correctness.

Outputs:

- Findings by severity.
- Test gaps.
- Release readiness recommendation.

## Iteration Loop

1. CEO reviews product direction and defines strategic priorities.
2. PM turns priorities into user journeys, requirements, and backlog.
3. VP Engineering turns backlog into architecture and milestone plan.
4. Lead agent splits work into disjoint engineering tasks.
5. Software engineers implement features in parallel.
6. Review / QA checks behavior, tests, safety, and product fit.
7. Lead agent integrates work and updates docs.
8. CEO/PM/VP Eng review completed work and choose next iteration.

## Communication Rules

- Every completed task must report:
  - What changed.
  - Files changed.
  - Tests run.
  - Product impact.
  - Remaining risks.

- Engineering agents must not revert each other's work.
- Engineering tasks should have disjoint file ownership when run in parallel.
- Strategic and product agents should not edit code directly.
- Technical planning agents should not overrule product priorities without naming tradeoffs.
- Product agents should not ship workflows without acceptance criteria.

## Suggested Cadence

Manual loop:

- Run CEO, PM, and VP Engineering review when strategy changes or a major feature completes.
- Run engineering agents for the next selected implementation batch.
- Run QA/review agent before considering a milestone complete.

Automated loop option:

- Daily PM/VP Eng backlog refinement.
- Twice-weekly engineering implementation batch.
- Weekly CEO strategy review.
- Review/QA after every implementation batch.

Automations should only be enabled after a concrete cadence and task scope are approved, because always-on agents can create cost, noise, and conflicting work without a tight backlog.

## Current Recommended Next Iteration

Focus on the trust wedge:

1. Add structured citation objects to chat responses.
2. Improve structured citation objects and claim-level support without adding noisy downloads to ordinary Q&A.
3. Add upload ingestion status in the UI.
4. Reintroduce click-to-inspect evidence for generated SCF values.
5. Add routing and retrieval evaluation cases for unsupported reporting questions.
