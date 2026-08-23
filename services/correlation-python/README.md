# G-CCI Cross-Source Correlation Service

Python/FastAPI service for cross-source transportation-event correlation, IncidentHypothesis generation, nearest-camera discovery, and expected-information-gain evidence-gap ranking.

## Runtime boundary

This service answers **whether records likely describe the same or related transportation event** and what evidence should be acquired next. It does not identify people, assign legal fault, authorize attorney outreach, or bypass the TypeScript compliance gate.

## Run

```bash
cd services/correlation-python
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\\Scripts\\activate
pip install -e ".[dev]"
pytest -q
uvicorn gcci.api:app --host 0.0.0.0 --port 8000
```

## Endpoint

`POST /correlate`

Input: normalized GDOT/GEMA/Waze-style event records and camera metadata.

Output: correlated incident packages containing pairwise factor scores, an IncidentHypothesis, contradictions, nearest cameras, evidence gaps, and explicit policy flags keeping party attribution/contact eligibility unevaluated.

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

## Production next steps

- durable PostgreSQL/PostGIS persistence
- worker/queue for continuous ingestion
- service authentication and mTLS/API gateway
- OpenTelemetry tracing and metrics
- calibrated correlation thresholds from labeled outcomes
- runtime RDF/SHACL projection
- ledger bridge to the canonical TypeScript evidentiary ledger
