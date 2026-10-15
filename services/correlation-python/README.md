# G-CCI Intelligence Service

FastAPI/PostgreSQL/PostGIS service for the durable G-CCI product path.

## Responsibility

This service owns:
- normalized event persistence;
- cross-source incident correlation and immutable hypothesis revisions;
- PostGIS camera/evidence discovery;
- canonical-score job orchestration to the internal TypeScript scorer;
- evidence acquisition priority;
- lead qualification and evidence-backed claimant resolution;
- durable compliance and encrypted contact storage;
- attorney feedback, case outcomes, and external benchmark validation;
- durable decision-ledger provenance;
- operational health/metrics and the authenticated external API boundary.

It does not collapse correlation into causation, attribution, case value, identity, contact eligibility, or outreach authorization.

## Product-critical flow

```text
event -> hypothesis revision -> score job -> canonical TypeScript score
      -> evidence priority -> ranked opportunity -> attorney review
      -> case outcome -> validation metrics
```

The product is under a broad feature freeze while this loop is validated.

## Validation

Migrations:
- `009_attorney_feedback_validation.sql` — attorney dispositions and case outcomes.
- `010_validation_benchmark_corpus.sql` — external historical ground truth.

Key endpoints:
- `GET /opportunities`
- `POST /hypotheses/{id}/attorney-review`
- `GET /hypotheses/{id}/attorney-reviews`
- `POST /hypotheses/{id}/outcomes`
- `POST /validation/benchmark-cases`
- `POST /validation/benchmark-cases/{id}/match`
- `GET /validation/benchmark-cases`
- `GET /validation/metrics?k=10`

Validation metrics are intentionally nullable when ground truth is insufficient.

## Durable state

PostgreSQL/PostGIS is authoritative for production analytical state. Tracked migrations are applied in lexical order by `python -m gcci.migrate` and CI applies them twice to test idempotency.

## Canonical scoring boundary

Python derives evidence-backed score inputs. The TypeScript service owns the canonical COS formula and version. Python persists the returned result and downstream investigation decisions. Do not duplicate the canonical score formula in Python.

## Run

```bash
docker compose up --build
```

Worker:

```bash
python -m gcci.worker
```

Tests:

```bash
python -m pip install -e ".[dev]"
ruff check gcci tests
pytest -q
```

## Release rule

Committed code is not production verification. Release requires GitHub CI to execute successfully, migration idempotency, integration tests, staging readiness/dependency health, ledger integrity, production identity/secrets/encryption, monitoring/backups, and zero unresolved Critical red-team findings.

See the repository root `README.md` and `PRODUCT_SUCCESS_PLAN.md` for the authoritative product strategy.
