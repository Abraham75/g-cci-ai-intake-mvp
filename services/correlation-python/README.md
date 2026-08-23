# G-CCI Cross-Source Correlation Service

Python/FastAPI service for cross-source transportation-event correlation, durable PostgreSQL/PostGIS persistence, versioned `IncidentHypothesis` management, canonical G-CCI Case Opportunity scoring, nearest-camera discovery, expected-information-gain evidence-gap ranking, and append-only decision-ledger provenance.

## Runtime boundary

This service answers **whether records likely describe the same or related transportation event**, whether a hypothesis revision is material enough to require re-scoring, and what evidence should be acquired next. It does not identify people, assign legal fault, authorize attorney outreach, or bypass the TypeScript compliance gate.

The following remain independent:

```text
Event Correlation
!= Causal Relationship
!= Party Attribution
!= Case Opportunity
!= Contact Eligibility
```

## Durable event -> score flow

```text
NormalizedEvent
    |
    v
PostgreSQL/PostGIS upsert
    |
    +--> Evidence ledger entry
    |
    v
Time + roadway + ST_DWithin candidate search
    |
    v
Correlation / clustering
    |
    v
Stable IncidentHypothesis
    |
    v
Immutable HypothesisRevision N
    |
    +--> hypothesis_events evidence links
    +--> Hypothesis ledger entry
    +--> supporting-evidence Assertion entries
    |
    v
Materiality evaluation
    |
    +-- non-material --> no redundant score job
    |
    `-- material --> durable score_jobs outbox
                         |
                         v
               TypeScript canonical scorer
               POST /api/scoring/score
                         |
                         v
                   score_results
                         |
                         +--> Score ledger entry
                         |
                         v
                    Tier A/B/C/D

Contact eligibility remains outside this path and requires the separate compliance gate.
```

If a source record changes, its `raw_sha256` no longer matches `correlation_processed_hash`; the worker reprocesses it and creates a new hypothesis revision rather than overwriting prior history.

## What makes a revision material

A revision is queued for canonical scoring when one or more of these occurs:

- first hypothesis revision
- correlation classification changes
- machine-confidence change meets the configured materiality threshold
- supporting-evidence membership changes
- contradiction set changes
- the derived canonical scoring input changes

The default machine-confidence materiality threshold is `0.05` and is configurable with `GCCI_SCORE_MATERIAL_CONFIDENCE_DELTA`.

## Canonical scoring boundary

The Python service **does not duplicate the canonical COS formula**. It derives evidence-backed scoring components and sends the canonical input contract to the TypeScript runtime at:

```text
POST /api/scoring/score
```

The TypeScript scorer owns:

```text
COS =
0.25 * Liability
+ 0.20 * Injury
+ 0.20 * Collectability
+ 0.15 * Evidence
+ 0.10 * MechanismSeverity
+ 0.10 * DefendantResolution
- 0.20 * UncertaintyPenalty
```

and the canonical tier thresholds:

- Tier A: `>= 0.80`
- Tier B: `>= 0.65`
- Tier C: `>= 0.45`
- Tier D: `< 0.45`
- any unresolved high-severity contradiction forces Tier C

Score-input derivation is versioned separately as `gcci-score-input-derivation-v1.0.0`. Correlation confidence is never silently converted into liability or party attribution.

## Database model

PostgreSQL 16 + PostGIS stores:

- `normalized_events` — source-normalized events with `geography(Point,4326)` geometry
- `incident_hypotheses` — stable incident identity and current revision pointer
- `hypothesis_revisions` — immutable machine-generated revisions
- `hypothesis_events` — version-aware supporting-evidence links
- `score_jobs` — durable canonical-scoring outbox with lease/retry state
- `score_results` — immutable score results by hypothesis revision
- `decision_ledger` — append-only SHA-256 hash-linked evidentiary ledger

The persistence path uses PostGIS `ST_DWithin` for spatial blocking and PostgreSQL advisory locks to serialize hypothesis create/revise selection and ledger hash-chain appends across multiple worker/API processes.

## Continuous worker

`python -m gcci.worker`

The worker performs two durable loops:

1. correlation processing for records whose `correlation_processed_hash` is missing or differs from the current source hash;
2. canonical scoring for material revisions queued in `score_jobs`.

Scoring jobs use `FOR UPDATE SKIP LOCKED`, a time-bounded `PROCESSING` lease, and exponential retry. A scorer/network outage does not roll back correlation or lose the score request.

## API

- `POST /correlate` — stateless analysis; no persistence
- `POST /events/ingest` — persist one event and correlate it transactionally
- `POST /events/ingest-batch` — event-isolated batch ingestion
- `GET /hypotheses/{id}` — current hypothesis revision
- `GET /hypotheses/{id}/revisions` — complete hypothesis history
- `GET /hypotheses/{id}/score` — latest canonical score plus pending-job state
- `GET /hypotheses/{id}/scores` — canonical score history by revision
- `GET /ledger/subject/{id}` — auditable ledger history for a subject
- `GET /ledger/integrity` — verify the persistent hash chain
- `GET /health` — service health

The TypeScript service additionally exposes:

- `POST /api/scoring/score` — canonical internal scoring contract

## Run the full stack

```bash
cd services/correlation-python
docker compose up --build
```

This starts:

- PostGIS on port `5432`
- canonical TypeScript G-CCI scorer on port `3001`
- FastAPI correlation service on port `8000`
- continuous correlation + scoring worker

Open API docs at:

```text
http://127.0.0.1:8000/docs
```

For a local Python environment instead:

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\\Scripts\\activate
pip install -e ".[dev]"
pytest -q
uvicorn gcci.api:app --host 0.0.0.0 --port 8000
```

The local TypeScript scorer must also be running:

```bash
npm install
npm run server
```

## Correlation factors

- temporal proximity
- spatial proximity
- roadway agreement
- direction compatibility
- mechanism similarity
- independent-source corroboration

## Evidence-gap ranking

Expected information gain is computed as:

```text
P(evidence exists)
* P(evidence resolves the question)
* materiality
* preservation urgency
```

Current evidence classes include CCTV, CAD/911, crash reports, tow records, EDR, ELD/telematics, and FMCSA carrier enrichment.

## Ledger semantics

The decision ledger is append-only by application contract. Hypothesis revisions use `supersedes_entry_id` to identify the prior machine conclusion without deleting or mutating it. Each supporting-evidence attachment/withdrawal is a separate assertion. Material score requests and canonical score results are separate ledger entries, preserving the exact revision and scoring input that produced each result.

Ledger rows are globally SHA-256 hash-linked, and a transaction-scoped PostgreSQL advisory lock serializes chain appends.

For production, the database role used by the application should receive `SELECT` and `INSERT` on `decision_ledger`, but no `UPDATE` or `DELETE` privileges.

## Remaining production hardening

- authenticated service-to-service scoring requests / network policy
- authenticated ingestion
- managed secrets rather than local `.env` credentials
- retry/dead-letter telemetry for upstream source adapters and canonical scorer
- OpenTelemetry traces, metrics, and structured logs
- database backups, PITR, and replication strategy
- calibrated component-derivation rules from attorney-reviewed outcomes
- calibrated correlation thresholds from labeled outcomes
- runtime RDF/SHACL projection of persisted hypothesis and score revisions
- migration from raw SQL bootstrap to Alembic once the schema stabilizes
