# G-CCI Multi-Agent Production Swarm

## Mission
Deliver a secure, testable, deployable G-CCI release. No agent may declare production readiness by assertion. Every finding needs a reproducer, severity, code owner, fix, and passing verification.

## Parallel specialist workstreams
| Agent | Scope | Required artifact | Gate |
|---|---|---|---|
| A1 Security adversary | JWT/OIDC, RBAC, service-to-service auth, vault, CORS, injection, secret leakage, abuse | Threat model, exploit repro, fixes and security tests | No Critical/High unresolved |
| A2 Database and audit | PostGIS migrations, concurrency, immutable revisions, hash-chain ledger, retention, backups | Migration tests, concurrent write tests, restore proof | Repeatable migrations and recoverable data |
| A3 Correlation and ML validation | Source dedup, time/geospatial errors, event vs causal vs attribution boundaries, score calibration | Historical benchmark harness, regression fixtures, false-positive analysis | Measured recall and ranking precision |
| A4 Legal/compliance | Contact-source provenance, Georgia solicitation gates, DPPA, suppression, authorization boundaries | Jurisdiction policy matrix, fail-closed tests, counsel-review checklist | No bypass from case value to outreach |
| A5 API/contracts | FastAPI/TypeScript contracts, schema drift, versioning, retries, idempotency, error handling | Contract tests and API failure tests | Contract compatibility |
| A6 Attorney UX/accessibility | Priority queue, case evidence, dispositions, prospect review, partial failure, keyboard accessibility | E2E tests and task-completion evidence | Critical journeys pass |
| A7 Platform/SRE | Docker, environments, CI runners, secrets, metrics, alerts, migrations, backups, rollback | Staging deploy, load tests, recovery exercise | Green CI + staging and rollback |
| A8 Red-team release auditor | Independently challenge all preceding agents, detect false claims and untested assumptions | Signed release decision with evidence links | Explicit GO / NO-GO |

## Dependency order
1. Reproduce CI execution failures and establish a trustworthy test runner.
2. Audit authentication and data-integrity boundaries before exposing new functionality.
3. Fix contract and migration failures.
4. Run isolated unit, integration, contract, and E2E suites.
5. Test negative cases, concurrency, source outages, malicious inputs, and legal gate bypasses.
6. Deploy to staging with production-like configuration.
7. Exercise backup restore, rollback, telemetry, and load.
8. Red-team independently verifies all evidence and issues GO / NO-GO.

## Required handoff contract
Every agent hands off:
- scope and files inspected;
- exact finding with severity and reproduction;
- patch/commit references;
- new or updated automated tests;
- test execution output and environment;
- residual risk and dependency;
- reviewer decision.

The orchestrator must reject unsupported 'passed' claims, preserve all semantic boundaries, and avoid concurrent writes to the same file.

## Release evidence manifest
A production release requires:
- actual executed and successful GitHub Actions jobs (not jobs that fail with zero steps);
- dependency/SAST/container and secret scans;
- database migration upgrade and repeatability results;
- PostGIS + canonical scorer integration tests;
- complete attorney UI E2E journeys;
- auth and compliance fail-closed adversarial tests;
- immutable ledger integrity and replay checks;
- staging deployment with real health/dependency probes;
- backup restore, rollback and load-test artifacts;
- reviewed Georgia/DPPA legal policy configuration;
- measured benchmark performance with documented acceptance thresholds;
- A8 independent GO decision.

Until all are satisfied the release state is **NO-GO**.

## Immediate defects identified
- Python validation endpoints existed but were not mounted in `gcci/api.py` (corrected).
- CI currently reports failures with no executed step information; the runner/workflow infrastructure needs investigation before verification can be claimed.
- Benchmark API must be security-tested for authorized reviewer identity, matching integrity, and tamper resistance.
- Ranking and KPI queries require real PostGIS integration tests, not only formula unit tests.

## Explicit operational constraint
This document defines workstreams and acceptance contracts; it does not falsely imply that independent background agents have been launched. Actual parallel execution requires available agent workers or a multi-agent runner, and each result must be verified in the repository.
