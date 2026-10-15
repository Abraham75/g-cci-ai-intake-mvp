# G-CCI Product Success Plan

## Product thesis

G-CCI succeeds only if it reliably identifies valuable commercial-trucking injury opportunities earlier than the firm's existing process, explains why they deserve attention, recommends the highest-value next investigative action, and learns from attorney decisions and real case outcomes.

The critical loop is:

```text
signals -> normalized events -> incident correlation -> canonical qualification
        -> ranked attorney queue -> evidence acquisition -> attorney disposition
        -> case outcome -> validation metrics -> calibration
```

Everything else is supporting infrastructure.

## Feature-freeze rule

Broad feature expansion is frozen until the validation loop produces enough ground truth to evaluate ranking quality. New work must materially improve one of:

1. discovery recall;
2. qualification precision / Precision@K;
3. time-to-discovery advantage;
4. investigation yield;
5. reliability/security of the critical production path.

Ontology, orchestration, visualization, new model families, RAG, graph databases, advanced ML, and CRM-like features are secondary unless they solve a measured bottleneck.

## Five essential systems

### 1. Signal acquisition
Ingest a deliberately small set of high-value, lawful incident sources reliably. Measure source freshness and how often known valuable benchmark cases generate observable signals.

### 2. Incident correlation
Determine whether records describe the same or related event. Correlation must remain separate from causation, liability, party attribution, claimant identity, and outreach eligibility.

### 3. Case qualification
Rank attorney attention. The canonical COS remains versioned and deterministic, but ranking quality—not the numerical score itself—is the product KPI.

### 4. Evidence acquisition
Convert uncertainty into a concrete investigation plan. The UI should emphasize the next best action and preservation urgency rather than exposing model mechanics.

### 5. Human feedback and outcomes
Every reviewed opportunity should receive an attorney disposition. Later case stages are captured as outcomes. These labels become the ground truth for calibration.

## Ground-truth data model

Migration 009 introduces immutable attorney reviews and case outcomes.

Attorney dispositions:
- GOOD_CASE
- BAD_CASE
- NEEDS_MORE_INFORMATION
- DUPLICATE
- NOT_A_TRUCK_CASE
- INSUFFICIENT_INJURY
- LIABILITY_TOO_WEAK
- NO_COLLECTIBLE_DEFENDANT
- ALREADY_REPRESENTED
- OTHER

Outcome stages:
- INVESTIGATED
- ADVANCED
- SIGNED
- DECLINED
- REFERRED
- LOST
- SETTLED

Migration 010 introduces an external benchmark corpus. Known valuable historical cases can be loaded independently of G-CCI and matched to discovered hypotheses only with explicit match evidence. This prevents the system from measuring recall against its own discoveries.

## Product KPIs

### Discovery recall
Known valuable benchmark cases matched to a G-CCI hypothesis / all known valuable benchmark cases.

### Precision@K
Among reviewed opportunities in the top K ranked results, the proportion attorneys label worth investigating. Unreviewed cases are not silently counted as negatives.

### Qualification precision
Attorney-worthy reviewed opportunities / all opportunities with a definitive attorney-worthy label.

### Investigation yield
Cases that advance after investigation / cases that enter an investigated or later stage.

### Time advantage
G-CCI hypothesis creation time minus traditional-awareness time for matched benchmark cases. Negative values mean G-CCI detected the opportunity earlier.

## Attorney UX

The primary navigation is intentionally reduced to:

1. Opportunity Radar
2. Case Intelligence
3. Platform Status

The Opportunity Radar is the default screen. It ranks durable scored hypotheses, shows the next best evidence action, captures attorney ground truth, and displays validation metrics only when enough data exists.

Decision economics, orchestration internals, ontology details, hashes, model-provider details, and infrastructure state are not primary attorney workflows.

## 90-day execution plan

### Phase 1 — Stabilize
- keep broad feature freeze;
- make CI execute reliably;
- maintain one external API boundary;
- apply migrations idempotently;
- verify auth/RBAC, encryption, audit, backups and observability in staging;
- reconcile documentation with the deployed architecture.

### Phase 2 — Build benchmark corpus
- select a defined historical Georgia commercial-trucking cohort;
- label known valuable and non-valuable incidents independently;
- record traditional-awareness timestamps when defensible;
- run the historical events through the same production pipeline;
- match benchmark cases to hypotheses with explicit evidence.

### Phase 3 — Attorney pilot
- one or a small number of attorneys/investigators use Opportunity Radar daily;
- require dispositions on reviewed opportunities;
- record investigation outcomes;
- review false positives, missed benchmark cases, and evidence recommendations weekly.

### Phase 4 — Calibrate
- compare ranking against attorney labels and outcomes;
- change weights/rules only when supported by validation evidence;
- version every scoring change;
- preserve prior results for regression comparison.

## Release gate

A release candidate requires:
- CI green;
- tracked migrations apply twice cleanly;
- Python tests green, including PostGIS/scorer integration;
- TypeScript and React production builds green;
- ontology validation green;
- no unresolved Critical red-team findings;
- staging readiness/dependency health green;
- ledger integrity green;
- security configuration uses production secrets/identity rather than development fallbacks.

A committed branch is not a verified release.

## Non-negotiable semantic boundary

```text
Event Correlation
!= Causal Relationship
!= Party Attribution
!= Case Opportunity
!= Lead Qualification
!= Claimant Resolution
!= Contact Eligibility
!= Outreach Authorization
```

Case value must never become permission to contact a person.
