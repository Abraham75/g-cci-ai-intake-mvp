# G-CCI Multi-Agent Production Orchestration

## Objective

G-CCI uses a coordinated role model for production engineering and decision-support work. The Orchestrator decomposes work, manages dependencies, validates handoffs, routes review findings, and makes release recommendations. It does not replace domain-specific engines or human legal judgment.

## Roles

- ORCHESTRATOR — decomposition, routing, dependency management, integration, release control.
- RESEARCHER — evidence gathering and source evaluation.
- ANALYST — structured reasoning, alternatives, tradeoffs, quantitative/risk analysis.
- WRITER — audience-specific drafting from approved evidence and assumptions only.
- TECHNICAL_SPECIALIST — architecture, APIs, implementation, debugging, tests, security and operations.
- CRITIC — independent Critical/Major/Minor red-team review with a proposed fix for every finding.
- EDITOR — final synthesis that preserves material disagreement and uncertainty.

## Epistemic contract

Every material claim is labeled `Verified`, `Inferred`, `Assumed`, or `Opinion`. A `Verified` claim is invalid without at least one evidence ID. This invariant is enforced by the Pydantic contract and by PostgreSQL for persisted claims.

## Task graph and handoffs

Every task has a unique ID, assigned role, objective, required output, quality bar, constraints, dependencies, assumptions, and optional human-approval requirement. The graph rejects missing dependencies, self-dependencies, duplicate IDs, and cycles. Independent ready tasks may execute in parallel.

Every handoff contains the task objective, inputs, artifacts, claims, confidence, unresolved questions, risks, and recommended next task. Downstream agents must not silently upgrade an Inferred or Assumed claim to Verified.

## Cross-review and release

Research evidence feeds analysis. Approved evidence and analysis may feed writing. Technical outputs are routed to Critic review. Material findings are routed back to the role best suited to correct them. Corrections are recorded in `orchestration_change_log`.

An unresolved `Critical` finding blocks release. Any task marked `requires_human_approval` also blocks release until approval is recorded. Major findings remain visible in the release decision even when they do not independently block release.

For G-CCI, identity resolution, sensitive contact access, compliance review, and outreach activation remain domain-controlled high-risk actions. The multi-agent Orchestrator cannot bypass the durable compliance gate or convert case value into contact eligibility.

## Persistence

Migration `008_multi_agent_orchestration.sql` adds `orchestration_runs`, `orchestration_tasks`, `agent_handoffs`, `evidence_claims`, `orchestration_review_findings`, `orchestration_change_log`, and `orchestration_release_decisions`.

The first implementation establishes contracts, graph validation, durable schema, release gating, and invariant tests. It intentionally does not pretend that independent external AI models are available inside the runtime. Model-provider execution should be introduced behind a provider-neutral adapter with timeouts, retries, model/version provenance, structured-output validation, token/cost budgets, and no direct authority over contact/outreach actions.
