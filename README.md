# G-CCI AI Intake MVP

**Graham Case Correlation Intelligence**

G-CCI is a lawyer-centric legal intelligence platform for catastrophic personal-injury and commercial-trucking litigation. The current MVP is evolving from a basic intake scorer into a broader case-discovery, incident-correlation, evidence, provenance, contradiction, party-resolution, and compliance-controlled decision platform.

The canonical runtime on the active integration branch is the TypeScript/Express service under `server/`.

---

## Executive Overview

G-CCI is designed to transform fragmented incident, intake, evidence, party, and compliance signals into explainable litigation intelligence.

The platform keeps five questions structurally separate:

1. **Event Correlation Confidence** — are records or events actually connected?
2. **Causal Relationship Confidence** — did one event cause or materially contribute to another?
3. **Party Attribution Confidence** — can responsibility be tied to a specific vehicle, person, carrier, or organization?
4. **Case Opportunity Score** — is the matter economically and legally worth deeper attorney investigation?
5. **Contact Eligibility** — is outreach legally and operationally permitted after compliance review?

A high Case Opportunity Score does not authorize outreach, and high event correlation does not automatically increase party attribution.

---

# Core Capabilities

## 1. Canonical Case Opportunity Scoring

G-CCI uses the canonical Case Opportunity Score formula:

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

All component inputs are normalized to `0–1`, and the final score is clamped to `0–1`.

### Tiering

```text
Tier A: COS >= 0.80
Tier B: COS >= 0.65
Tier C: COS >= 0.45
Tier D: COS < 0.45
```

An unresolved high-severity contradiction forces an opportunity to **Tier C**, regardless of the raw COS.

The current scoring weights and mechanism-severity values are explicit but illustrative and are not yet calibrated against real outcomes.

---

## 2. Separate Confidence Dimensions

```text
Event Correlation Confidence
!= Causal Relationship Confidence
!= Party Attribution Confidence
```

Party attribution is not increased by lead value, contact completeness, event correlation, or causation alone.

---

## 3. Temporal Evidence Model

G-CCI preserves different clocks as different facts rather than collapsing them into one timestamp.

Supported temporal fields include:

- event occurrence time
- first call time
- CAD creation time
- first detection time
- unit arrival time
- record creation time
- source time
- ingestion time
- effective time
- clock uncertainty

This supports later crash-sequence reconstruction, secondary-event analysis, and multi-source timeline reasoning.

---

## 4. Formal RDF/OWL Ontology

The repository includes the formal G-CCI ontology package under `ontology/`.

The semantic contract covers:

- incidents and incident records
- roadway and infrastructure entities
- vehicles and commercial motor vehicles
- motor carriers
- evidence and observations
- temporal observations
- parties and party roles
- identity-resolution states
- liability signals
- correlation assertions
- causation assertions
- party-attribution assertions
- competing hypotheses
- contradictions
- case opportunities
- evidence gaps
- compliance states
- provenance
- immutable decision-ledger entries

### Core Semantic Invariants

1. Records are not incidents.
2. Multiple records may describe one underlying event.
3. Multiple incidents may be related without being merged.
4. Event correlation, causation, and attribution remain separate.
5. Access classification is separate from evidentiary strength.
6. Case value is separate from contact permission.
7. Human adjudication does not overwrite original machine output.
8. Corrections supersede prior entries rather than deleting history.
9. Temporal clocks remain distinct.
10. Material decisions retain provenance.

---

## 5. SHACL Validation

The ontology package contains SHACL constraints for incident structure, evidence, parties, hypotheses, opportunities, confidence dimensions, compliance states, and ledger entries.

Validation tooling is provided under:

```text
scripts/validate_ontology.py
```

---

## 6. Temporal Evidence + Provenance + Decision Ledger

The runtime includes an append-only decision ledger under:

```text
server/ontology/ledger.ts
```

Ledger entry types include:

- Evidence
- TemporalObservation
- Assertion
- Hypothesis
- Score
- Contradiction
- HumanAdjudication
- ComplianceDecision
- Explanation
- RagRetrieval

Entries retain subject ID, payload, producer, timestamp, source system, model version, input ledger-entry IDs, supersession references, and sequential hashes.

### Current Production Limitation

The ledger is currently in-memory and resets when the process restarts. Production deployment should move this contract to durable append-only persistence with database-level protections and transactional hash-chain enforcement.

---

## 7. Provenance-First Intake Flow

```text
POST /api/intake
        |
        v
Preserve Raw Intake / Evidence
        |
        v
Temporal Normalization
        |
        v
Automatic Contradiction Detection
        |
        v
Canonical Case Opportunity Scoring
        |
        v
Tier Override if High-Severity Conflict Is Unresolved
        |
        v
Append Evidence + TemporalObservation + Contradiction + Score to Ledger
        |
        v
Return Score + Confidence + Contradictions + Ledger Reference
```

The score ledger entry references the evidence, temporal observation, and contradiction ledger entries used to derive the decision.

---

## 8. Contradiction Engine

The load-bearing contradiction engine is implemented under:

```text
server/ai/contradictions.ts
```

It scans evidence attributes for multiple distinct asserted values for the same attribute.

Examples include:

```text
vehicle_color: white vs blue
vehicle_type: work_truck vs suv
license_plate: conflicting values
carrier_name: conflicting values
incident_time: conflicting times
travel_direction: EB vs WB
```

Contradictions are first-class records with:

- contradiction ID
- subject ID
- attribute key
- all distinct conflicting values
- supporting evidence/source references
- severity
- detection timestamp
- resolution state
- analyst resolution details

### Severity Rules

Current illustrative severity assignments include:

```text
HIGH
vehicle_color
vehicle_type
license_plate
carrier_name

MEDIUM
incident_time
travel_direction
lane

LOW
weather
road_condition
```

Unlisted attributes default to medium severity.

### Tier-C Enforcement

The contradiction engine now feeds the canonical scorer directly.

```text
unresolved high-severity contradiction
        ->
contradictionCountsFor(subjectId)
        ->
ScoreIntakeInput.contradictions
        ->
classifyTier(...)
        ->
Tier C forced
```

The previous hardcoded `{ highSeverityUnresolved: 0, other: 0 }` bridge has been removed from the runtime.

### Human Resolution

An analyst may resolve a contradiction only when:

- at least one evidence reference is supplied, and
- the accepted value is one of the values actually asserted in the contradiction record.

The original machine-detected contradiction is not deleted. Resolution is added as a new ledger event.

### Current Limitation

Attribute comparison is exact-string based. Semantic equivalence, numeric tolerances, time-window reconciliation, and color-family matching are future work.

---

## 9. Compliance / Activation Gate

The safety-critical compliance gate is implemented under:

```text
server/compliance/gate.ts
```

A subject becomes contact-eligible only when:

```text
Legal Access Basis established
+
Solicitation Review = ClearedByCounsel
+
Suppression / Do-Not-Contact Check completed
=
Eligible
```

The gate never reads the Case Opportunity Score.

Both blocked and approved activation attempts are written to the decision ledger.

---

## 10. Party Resolution Ladder

```text
UNKNOWN
  -> CANDIDATE
  -> CORROBORATED
  -> VERIFIED
```

Party progression is separate from compliance status. A party cannot advance without evidence references, and every advancement is ledgered.

The current module stores structural roles and resolution state only. It does not yet expose protected identity or contact information.

---

# Runtime APIs

| Endpoint | Description |
| --- | --- |
| `POST /api/intake` | Normalize intake, detect contradictions, score opportunity, and write provenance ledger entries |
| `GET /api/ontology` | Return ontology version and runtime invariants |
| `GET /api/ledger/integrity` | Check the in-memory ledger hash chain |
| `GET /api/ledger/subject/:subjectId` | Return complete subject ledger history |
| `GET /api/ledger/provenance/:entryId` | Return provenance chain for a ledger entry |
| `GET /api/compliance/:subjectId/gate` | Return current compliance gate state |
| `POST /api/compliance/:subjectId/review` | Submit human compliance-review facts |
| `POST /api/compliance/:subjectId/activate` | Attempt activation; blocked unless eligible |
| `POST /api/compliance/:subjectId/parties` | Register a role-based party |
| `GET /api/compliance/:subjectId/parties` | Return parties for a subject |
| `POST /api/compliance/parties/:partyId/advance` | Advance a party one stage with evidence references |
| `POST /api/contradictions/subject/:subjectId/detect` | Detect contradictions for supplied evidence |
| `GET /api/contradictions/subject/:subjectId` | Return contradictions for a subject |
| `GET /api/contradictions/subject/:subjectId/counts` | Return scorer-ready contradiction counts |
| `POST /api/contradictions/:contradictionId/resolve` | Resolve a contradiction with analyst and evidence references |

---

# Current Runtime Architecture

```text
Client / Intake Source
        |
        v
TypeScript / Express API
server/index.ts
        |
        +----------------------+----------------------+
        |                      |                      |
        v                      v                      v
Intake / Triage       Contradiction Engine      Compliance Gate
server/ai/triage.ts   server/ai/contradictions.ts server/compliance/gate.ts
        |                      |                      |
        +----------+-----------+                      |
                   |                                  |
                   v                                  v
          Canonical COS Engine                Contact Eligibility
          server/ai/scoring.ts                Party Resolution
                   |                                  |
                   +----------------+-----------------+
                                    |
                                    v
                          G-CCI Ontology Runtime
                          server/ontology/model.ts
                                    |
                                    v
                          Immutable Decision Ledger
                          server/ontology/ledger.ts
                                    |
                                    v
                          Provenance / Audit APIs
```

---

# Repository Structure

```text
g-cci-ai-intake-mvp/
|
+-- server/
|   +-- index.ts
|   +-- ai/
|   |   +-- scoring.ts
|   |   +-- triage.ts
|   |   +-- contradictions.ts
|   +-- compliance/
|   |   +-- gate.ts
|   +-- ontology/
|   |   +-- model.ts
|   |   +-- ledger.ts
|   +-- routes/
|       +-- intake.ts
|       +-- ontology.ts
|
+-- ontology/
|   +-- README.md
|   +-- gcci_formal_ontology_v1.0.0.zip
|
+-- scripts/
|   +-- validate_ontology.py
|
+-- .github/workflows/
|   +-- ci.yml
|
+-- package.json
+-- tsconfig.json
```

---

# Development Status

## Implemented / Integrated

- canonical TypeScript Case Opportunity Score formula
- Tier A/B/C/D classification
- automatic contradiction detection from evidence attributes
- severity-aware contradiction classification
- contradiction-to-scorer integration
- unresolved high-severity contradiction forcing Tier C
- analyst contradiction resolution with evidence references
- contradiction detection and resolution ledger entries
- uncertainty penalty derived from contradiction counts
- separate event-correlation confidence
- separate causal-relationship confidence
- separate party-attribution confidence
- mechanism-severity model
- temporal evidence normalization
- ontology-aligned runtime types
- formal RDF/OWL ontology package
- SHACL validation package
- provenance-aware append-only ledger interface
- hash-linked ledger sequence
- intake -> temporal -> contradiction -> scoring provenance chain
- ontology metadata endpoint
- ledger integrity endpoint
- provenance-chain endpoint
- compliance review gate
- hard activation blocking
- audit logging of successful and blocked activation attempts
- role-based party registration
- controlled UNKNOWN -> CANDIDATE -> CORROBORATED -> VERIFIED progression

## Still In Progress

- tolerance-aware and semantic contradiction comparison
- full hypothesis engine with competing explanations
- human adjudication endpoints for hypotheses
- evidence-gap / expected-information-gain engine
- live RDF generation from runtime objects
- SHACL validation inside the live ingestion request path
- persistent graph database
- durable decision-ledger persistence
- road-network and trajectory physics
- clock-offset reconciliation
- source-reliability weighting
- separate calibrated car vs. CMV models
- trained XGBoost model
- real SHAP explanations
- RAG retrieval against the legal corpus
- production identity-resolution integrations
- live GDOT / CAD / FMCSA / towing / EDR / ELD connectors
- attorney CRM or case-management handoff

---

# Local Development

```bash
npm install
npm run build
npm run server
```

Default runtime:

```text
http://localhost:3001
```

Ontology validation:

```bash
python -m pip install rdflib pyshacl
python scripts/validate_ontology.py
```

---

# Product Design Principle

```text
Event Correlation
        !=
Causal Relationship
        !=
Party Attribution
        !=
Case Opportunity
        !=
Contact Eligibility
```

G-CCI is not intended to be a list broker or a single black-box lead score. It is being built as an explainable case-discovery and litigation-intelligence system where material conclusions are reproducible from evidence and provenance.

---

# Strategic Vision

The long-term platform should be capable of:

- discovering potentially valuable crash events
- correlating fragmented reports across multiple sources
- reconstructing event timelines
- identifying possible causal chains
- automatically surfacing contradictions
- ranking evidence gaps by expected information gain
- resolving vehicles, carriers, and parties through evidence-backed workflows
- prioritizing high-value trucking and severe-injury matters
- explaining scores and recommendations
- preserving provenance and decision history
- enforcing compliance before outreach or activation
- generating litigation-ready intelligence for attorney review

---

# Important Disclaimer

This repository is currently an MVP/prototype. Synthetic and demonstration data may be used. Illustrative scoring weights, contradiction severities, and confidence formulas are not outcome-calibrated, and the system is not legal advice.

Compliance, privacy, solicitation, DPPA, open-records, evidentiary, and professional-responsibility decisions must be reviewed and configured with qualified counsel before production use.

---

**Author:** Abraham Gilbert  
**License:** Proprietary MVP Prototype
