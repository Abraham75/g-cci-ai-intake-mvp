# G-CCI Cross-Source Correlation Service

Python/FastAPI service for cross-source transportation-event correlation, durable PostgreSQL/PostGIS persistence, versioned `IncidentHypothesis` management, canonical G-CCI Case Opportunity scoring, persistent camera intelligence, expected-information-gain evidence-gap ranking, score-conditioned evidence acquisition prioritization, and append-only decision-ledger provenance.

## Runtime boundary

This service answers whether records likely describe the same or related transportation event, whether a hypothesis revision is material enough to require re-scoring, which cameras are spatially/semantically relevant to the current hypothesis revision, and what evidence should be acquired next.

It does **not** identify people, assign legal fault, authorize attorney outreach, or bypass the TypeScript compliance gate.

```text
Event Correlation
!= Causal Relationship
!= Party Attribution
!= Case Opportunity
!= Camera Relevance
!= Evidence Acquisition Priority
!= Contact Eligibility
```

## Durable event -> hypothesis -> camera -> score -> investigation flow

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
Cross-source correlation / clustering
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
    +--> PostGIS camera candidate refresh
    |       |
    |       +--> distance in meters
    |       +--> roadway compatibility
    |       +--> direction compatibility
    |       +--> preservation time window
    |       `--> CameraCandidateSet ledger entry
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
                         |
                         v
                Evidence-gap ranking
                         |
                         v
             Evidence Acquisition Priority
                         |
                         +--> evidence_acquisition_tasks
                         `--> EvidenceAcquisitionPriority ledger entries

Contact eligibility remains outside this path and requires the separate compliance gate.
```

If a source record changes, its `raw_sha256` no longer matches `correlation_processed_hash`; the worker reprocesses it and creates a new hypothesis revision instead of overwriting prior history.

## Persistent camera intelligence

Camera inventory is now a first-class PostGIS resource rather than an ephemeral array passed to `/correlate`.

`traffic_cameras` stores:

- stable camera ID and source record ID
- source system
- name
- roadway and direction
- latitude/longitude
- `geography(Point,4326)` geometry
- snapshot URL and stream URL when supplied by the source
- active state
- raw normalized source payload
- first/last observation timestamps

`hypothesis_camera_candidates` stores the reproducible camera set for each hypothesis revision:

- hypothesis ID + revision
- camera ID
- metric distance from hypothesis centroid
- roadway match
- direction match
- evidence-discovery relevance score
- preservation-window start/end
- lifecycle state (`CURRENT` / `SUPERSEDED`)

Camera relevance is intentionally narrow:

```text
CameraRelevance =
0.70 * DistanceScore
+ 0.20 * RoadwayMatch
+ 0.10 * DirectionMatch
```

It does not infer causation or party identity.

The default search radius is 4,000 meters and the default preservation window extends 10 minutes before and after the hypothesis evidence interval. Both are configurable:

```text
GCCI_CAMERA_SEARCH_RADIUS_METERS
GCCI_MAX_CAMERA_RESULTS
GCCI_CAMERA_PRESERVATION_BEFORE_MINUTES
GCCI_CAMERA_PRESERVATION_AFTER_MINUTES
```

Every hypothesis revision automatically refreshes its candidate set. Older candidate sets are retained as `SUPERSEDED`; they are not deleted. Explicit refresh is also available when the camera inventory changes without a hypothesis revision.

## What makes a hypothesis revision material

A revision is queued for canonical scoring when one or more of these occurs:

- first hypothesis revision
- correlation classification changes
- machine-confidence change meets the configured materiality threshold
- supporting-evidence membership changes
- contradiction set changes
- derived canonical scoring input changes

The default confidence materiality threshold is `0.05`, configurable with `GCCI_SCORE_MATERIAL_CONFIDENCE_DELTA`.

## Canonical scoring boundary

The Python service does **not** duplicate the canonical COS formula. It derives evidence-backed scoring components and sends the canonical input contract to the TypeScript runtime:

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

Canonical tiers:

- Tier A: `>= 0.80`
- Tier B: `>= 0.65`
- Tier C: `>= 0.45`
- Tier D: `< 0.45`
- unresolved high-severity contradiction forces Tier C

Correlation confidence is never silently converted into liability or party attribution.

## Evidence acquisition priority

Evidence gaps are first ranked by expected information gain:

```text
EIG =
P(evidence exists)
* P(evidence resolves the question)
* materiality
* preservation urgency
```

The investigation queue then computes a separate Acquisition Priority Score:

```text
APS = EIG * (0.55 + 0.45 * COS) * TierMultiplier
```

Case economics modulate investigation urgency; they do not erase evidentiary value. Contact eligibility is not an input.

Only acquisition tasks tied to the newest completed score revision remain `OPEN`. Older revision tasks are retained as `SUPERSEDED`.

## Database model

PostgreSQL 16 + PostGIS stores:

- `normalized_events`
- `incident_hypotheses`
- `hypothesis_revisions`
- `hypothesis_events`
- `traffic_cameras`
- `hypothesis_camera_candidates`
- `score_jobs`
- `score_results`
- `evidence_acquisition_tasks`
- `decision_ledger`

The persistence path uses PostGIS `ST_DWithin` and `ST_Distance` for event and camera spatial operations and PostgreSQL advisory locks for concurrency-critical hypothesis/ledger paths.

Migrations are applied in lexical order:

```text
001_postgis_persistence.sql
002_hypothesis_event_lifecycle.sql
003_canonical_scoring_outbox.sql
004_evidence_acquisition_queue.sql
005_camera_inventory_and_hypothesis_candidates.sql
```

## API

Core correlation and scoring state:

- `POST /correlate` — stateless correlation analysis
- `POST /events/ingest`
- `POST /events/ingest-batch`
- `GET /hypotheses/{id}`
- `GET /hypotheses/{id}/revisions`
- `GET /hypotheses/{id}/score`
- `GET /hypotheses/{id}/scores`
- `GET /hypotheses/{id}/acquisition-tasks`
- `GET /acquisition-queue`

Camera intelligence:

- `POST /cameras/ingest-batch` — persist/upsert camera inventory
- `GET /cameras/status` — inventory counts/freshness
- `GET /hypotheses/{id}/cameras` — persisted revision-scoped candidates
- `POST /hypotheses/{id}/cameras/refresh` — explicit re-evaluation against current inventory

Auditability:

- `GET /ledger/subject/{id}`
- `GET /ledger/integrity`
- `GET /health`

The TypeScript service additionally exposes `POST /api/scoring/score` as the canonical internal scoring contract.

## Continuous worker

```bash
python -m gcci.worker
```

The worker performs durable correlation and canonical-scoring loops. Camera candidate refresh happens transactionally when a hypothesis revision is persisted, so scorer availability is not required for camera discovery.

## Run the full stack

```bash
cd services/correlation-python
docker compose up --build
```

Services:

- PostGIS `:5432`
- TypeScript canonical scorer `:3001`
- FastAPI correlation/camera service `:8000`
- continuous correlation + scoring worker

Open FastAPI docs at `http://127.0.0.1:8000/docs`.

## Case Intelligence Detail UI

The React attorney workspace consumes the persistent endpoints directly. Its **Map & Cameras** tab displays:

- current camera inventory count/freshness
- revision-scoped nearest camera candidates
- incident centroid and camera coordinates
- distance
- roadway and direction matches
- camera relevance
- preservation window
- snapshot/stream source links when available

The initial spatial display is dependency-free so the API contract can stabilize before adopting MapLibre. A future MapLibre implementation can replace the renderer without changing the persisted camera or hypothesis contracts.

## Ledger semantics

The decision ledger is append-only by application contract. Hypothesis revisions, camera candidate sets, score requests, score results, acquisition-priority decisions, and evidence-link changes are distinct ledger entries. Camera candidate entries cite the hypothesis revision entry that caused the search.

Ledger rows are globally SHA-256 hash-linked, with a transaction-scoped PostgreSQL advisory lock serializing chain appends.

## Remaining production hardening

- connect the public GDOT ArcGIS/511 camera adapter directly to `POST /cameras/ingest-batch` or the repository service
- scheduled camera inventory refresh and stale-camera deactivation policy
- MapLibre roadway basemap and optional camera field-of-view metadata
- authenticated ingestion and service-to-service scoring
- managed secrets / network policy
- production observability and alerting
