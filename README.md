# G-CCI — Graham Case Correlation Intelligence

G-CCI is an attorney-facing commercial-trucking case-discovery and investigation platform. Its product objective is narrow: **identify valuable trucking-injury opportunities earlier, rank them for attorney attention, recommend the highest-value next investigative action, and learn from attorney decisions and case outcomes.**

## Critical product loop

```text
Public incident signals
  -> normalization
  -> cross-source incident correlation
  -> durable IncidentHypothesis
  -> canonical Case Opportunity scoring
  -> attorney Opportunity Radar
  -> evidence acquisition / uncertainty reduction
  -> attorney disposition
  -> case outcome
  -> validation and calibration
```

The project is under a broad feature freeze while this loop is validated. See `PRODUCT_SUCCESS_PLAN.md`.

## Runtime architecture

- **React attorney console** — Opportunity Radar, Case Intelligence, Platform Status.
- **Python/FastAPI external API** — durable correlation, PostGIS persistence, camera/evidence intelligence, lead qualification, product validation, compliance and protected-contact workflows.
- **TypeScript/Express internal runtime** — canonical deterministic Case Opportunity scorer and source/runtime integrations.
- **PostgreSQL/PostGIS** — authoritative event, hypothesis, score, evidence, camera, prospect, compliance, contact, feedback, benchmark and decision-ledger state.
- **Decision ledger** — durable provenance for material analytical and human decisions.
- **RDF/OWL + SHACL** — semantic contract and validation assets, not the primary user experience.

## Product validation

The repository now captures two independent forms of ground truth.

### Attorney feedback
Migration `009_attorney_feedback_validation.sql` adds immutable attorney case reviews and case outcomes. Reviews are tied to the score revision seen by the reviewer and material reviews/outcomes are ledgered.

### External benchmark corpus
Migration `010_validation_benchmark_corpus.sql` stores historical known cases independently of G-CCI discovery. A benchmark case can be matched to a hypothesis only through an explicit reviewed match, allowing discovery recall and time advantage to be measured without using the system's own discoveries as ground truth.

Primary KPIs:
- discovery recall;
- Precision@K;
- qualification precision;
- investigation yield;
- time-to-discovery advantage.

No KPI is fabricated when ground truth is absent; the API returns `null` until the required labels exist.

## Attorney workflow

The default UI is **Opportunity Radar**. It ranks scored hypotheses, shows the next best evidence action, and captures attorney dispositions directly in the workflow. The primary navigation is intentionally limited to:

1. Opportunity Radar
2. Case Intelligence
3. Platform Status

Advanced model, ontology, orchestration and infrastructure details remain secondary/audit concerns.

## Semantic invariants

```text
Event Correlation Confidence
!= Causal Relationship Confidence
!= Party Attribution Confidence
!= Case Opportunity Score
!= Lead Qualification
!= Claimant Resolution
!= Contact Eligibility
!= Outreach Authorization
```

High case value never authorizes outreach. Camera relevance never establishes causation or party identity. Identity resolution must be evidence-backed. Compliance remains an independent durable gate.

## Canonical Case Opportunity Score

The TypeScript runtime remains the single owner of the canonical heuristic score:

```text
COS =
0.25 * Liability
+ 0.20 * Injury
+ 0.20 * Collectability
+ 0.15 * Evidence
+ 0.10 * Mechanism Severity
+ 0.10 * Defendant Resolution
- 0.20 * Uncertainty Penalty
```

Tier A >= 0.80, B >= 0.65, C >= 0.45, D otherwise. An unresolved high-severity contradiction forces Tier C.

These weights are **not treated as empirically calibrated truth**. Attorney labels and the external benchmark corpus exist specifically to test and later calibrate ranking quality.

## Production release gate

A commit is not a release. Production candidacy requires:
- GitHub CI actually executes and passes;
- TypeScript build passes;
- React production build passes;
- Python lint/tests pass, including PostGIS and canonical-scorer integration;
- migrations apply idempotently;
- ontology/SHACL validation passes;
- no unresolved Critical red-team findings;
- staging readiness/dependency checks pass;
- durable ledger integrity passes;
- production identity, secrets, encryption, monitoring and backup configuration are verified.

## Development

TypeScript:

```bash
npm install
npm run build
npm run build:server
```

Python/PostGIS stack:

```bash
cd services/correlation-python
docker compose up --build
```

Python tests:

```bash
cd services/correlation-python
python -m pip install -e ".[dev]"
pytest -q
```

Ontology validation:

```bash
python -m pip install rdflib pyshacl
python scripts/validate_ontology.py
```

## Current status

This branch is a production-hardening and validation candidate, not a production declaration. Live pilot performance, benchmark recall, ranking precision and investigation yield must be established with real reviewed data before the product's analytical effectiveness can be claimed.

For the authoritative product priorities and 90-day validation plan, see `PRODUCT_SUCCESS_PLAN.md`. For multi-agent engineering governance, see `MULTI_AGENT_ORCHESTRATION.md`.

**Author:** Abraham Gilbert  
**License:** Proprietary
