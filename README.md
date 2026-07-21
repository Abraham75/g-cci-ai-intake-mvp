# G-CCI AI Intake MVP

**Graham Case Correlation Intelligence**

G-CCI is a lawyer-centric legal intelligence platform for catastrophic personal-injury and commercial-trucking litigation. The current MVP is evolving from a basic intake scorer into a broader case-discovery, incident-correlation, evidence, provenance, and compliance-controlled decision platform.

The canonical runtime on the active integration branch is now the TypeScript/Express service under `server/`.

---

## Executive Overview

G-CCI is designed to transform fragmented incident, intake, evidence, party, and compliance signals into explainable litigation intelligence.

The platform is intended to help attorneys answer five different questions without collapsing them into one score:

1. **Event Correlation Confidence** — are two records or events actually connected?
2. **Causal Relationship Confidence** — did one event cause or materially contribute to another?
3. **Party Attribution Confidence** — can responsibility be tied to a specific vehicle, person, carrier, or organization?
4. **Case Opportunity Score** — is the matter economically and legally worth deeper attorney investigation?
5. **Contact Eligibility** — is outreach legally and operationally permitted after compliance review?

These dimensions are intentionally separate. A high Case Opportunity Score does not authorize outreach, and a high event-correlation score does not increase party attribution automatically.

---

# Core Capabilities

## 1. Canonical Case Opportunity Scoring

G-CCI now uses the canonical Case Opportunity Score formula:

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

An unresolved high-severity contradiction forces the opportunity to **Tier C**, regardless of the raw COS.

The current mechanism-severity values are illustrative and not yet outcome-calibrated.

---

## 2. Separate Confidence Dimensions

The scoring runtime keeps these three confidence measures independent:

```text
Event Correlation Confidence
!= Causal Relationship Confidence
!= Party Attribution Confidence
```

### Event Correlation

Measures whether records or events appear connected.

### Causal Relationship

Measures whether one incident likely caused or contributed to another.

### Party Attribution

Measures whether a specific party can be supported by verified evidence.

Party attribution is not increased by lead value, contact completeness, event correlation, or causation alone.

---

## 3. Temporal Evidence Model

G-CCI preserves different clocks as different facts rather than collapsing them into a single timestamp.

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

This is especially important when reconstructing crash sequences, secondary incidents, debris events, and multi-source timelines.

---

## 4. Formal RDF/OWL Ontology

The repository includes the formal G-CCI ontology package under `ontology/`.

The ontology defines the semantic contract for:

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

The formal package includes RDF/OWL vocabularies, SHACL validation shapes, synthetic Phillips/Event5122820 example data, and SPARQL competency queries.

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
10. Material decisions must retain provenance.

---

## 5. SHACL Validation

The ontology package contains SHACL constraints for:

- incident structure
- incident-record linkage
- evidence requirements
- party-resolution data
- hypotheses
- case-opportunity scores
- confidence dimensions
- contact-eligibility conditions
- ledger-entry structure

The repository also includes ontology validation tooling intended to parse all Turtle files and run SHACL validation against the synthetic demonstration graph.

---

## 6. Temporal Evidence + Provenance + Decision Ledger

The runtime now includes an append-only decision ledger under:

```text
server/ontology/ledger.ts
```

The ledger records material machine and human events, including:

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

Every entry can retain:

- subject ID
- payload
- producing service or human reviewer
- production timestamp
- source system
- model version
- input ledger-entry IDs
- supersession reference
- previous hash
- entry hash

The current implementation is process-local and in-memory, but entries are SHA-256 hash-linked so tampering with sequence relationships can be detected.

### Important Production Limitation

The current ledger resets when the server restarts. Production deployment should move this contract to durable append-only persistence such as PostgreSQL or an event store, with database-level protections and transactional hash-chain enforcement.

---

## 7. Provenance-First Intake Flow

The current TypeScript intake path follows this pattern:

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
Canonical Case Opportunity Scoring
        |
        v
Append Evidence + TemporalObservation + Score to Ledger
        |
        v
Return Scoring + Confidence + Ledger Reference
```

Every score can therefore be traced back to the input and temporal-normalization entries that produced it.

---

## 8. Compliance / Activation Gate

G-CCI now includes a safety-critical compliance gate under:

```text
server/compliance/gate.ts
```

The gate makes **Case Opportunity Score** and **permission to contact** fully independent.

A subject becomes contact-eligible only when all required controls are satisfied:

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

A Tier A opportunity with no lawful access basis is still ineligible for activation.

### Activation Behavior

Blocked and approved activation attempts are both written to the decision ledger.

The runtime does not infer legal access or solicitation clearance automatically. These are human-supplied review decisions.

No unverified identity or contact information is introduced by the compliance module.

---

## 9. Party Resolution Ladder

The current runtime supports the controlled party-resolution progression:

```text
UNKNOWN
  -> CANDIDATE
  -> CORROBORATED
  -> VERIFIED
```

Party identity progress is separate from compliance status.

A party cannot move forward without evidence references, and stage advancement is recorded in the ledger.

Current party records contain structural role and resolution state only; they do not yet store or return names, phone numbers, addresses, or other protected identity data.

Supported roles include:

- Driver
- Registered Owner
- Motor Carrier
- Witness
- Injured Party

---

## 10. Ontology and Ledger Audit APIs

The TypeScript runtime exposes ontology and audit endpoints.

| Endpoint | Description |
| --- | --- |
| `POST /api/intake` | Accept intake data, normalize time, score opportunity, and write provenance ledger entries |
| `GET /api/ontology` | Return ontology version and runtime invariants |
| `GET /api/ledger/integrity` | Check the in-memory ledger hash chain |
| `GET /api/ledger/subject/:subjectId` | Return the complete ledger history for a subject |
| `GET /api/ledger/provenance/:entryId` | Return the provenance chain for a ledger entry |
| `GET /api/compliance/:subjectId/gate` | Return current compliance gate state |
| `POST /api/compliance/:subjectId/review` | Submit human compliance-review facts |
| `POST /api/compliance/:subjectId/activate` | Attempt activation; blocked unless the gate is eligible |
| `POST /api/compliance/:subjectId/parties` | Register a role-based party record |
| `GET /api/compliance/:subjectId/parties` | Return parties associated with a subject |
| `POST /api/compliance/parties/:partyId/advance` | Advance a party one verification stage with supporting evidence references |

---

# Current Runtime Architecture

```text
Client / Intake Source
        |
        v
TypeScript / Express API
server/index.ts
        |
        +------------------------------+
        |                              |
        v                              v
Intake / Triage                  Compliance Gate
server/ai/triage.ts              server/compliance/gate.ts
        |                              |
        v                              v
Canonical COS Engine             Contact Eligibility
server/ai/scoring.ts             Party Resolution Ladder
        |                              |
        +---------------+--------------+
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

The formal RDF/OWL/SHACL ontology lives under `ontology/` and is the semantic contract the runtime is being aligned to.

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
- intake -> temporal -> scoring provenance chain
- ontology metadata endpoint
- ledger integrity endpoint
- provenance-chain endpoint
- compliance review gate
- hard activation blocking
- audit logging of successful and blocked activation attempts
- role-based party registration
- controlled UNKNOWN -> CANDIDATE -> CORROBORATED -> VERIFIED progression

## Still In Progress

The following capabilities are not yet fully load-bearing in the TypeScript runtime:

- automatic contradiction detection from evidence attributes
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

Install dependencies:

```bash
npm install
```

Run the TypeScript compiler check:

```bash
npm run build
```

Start the server:

```bash
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

G-CCI is not intended to be a list broker or a single black-box lead score.

It is being built as an explainable case-discovery and litigation-intelligence system where every material conclusion should be reproducible from evidence and provenance.

The platform's core decision boundary is:

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

That separation protects analytical integrity, reduces false attribution, and prevents a commercially attractive case from silently becoming an unauthorized outreach decision.

---

# Strategic Vision

G-CCI is intended to become the semantic and analytical layer between raw transportation-event data and attorney decision-making.

The long-term platform should be capable of:

- discovering potentially valuable crash events
- correlating fragmented reports across multiple data sources
- reconstructing event timelines
- identifying possible causal chains
- surfacing contradictions and evidence gaps
- resolving vehicles, carriers, and parties through evidence-backed workflows
- prioritizing high-value trucking and severe-injury matters
- explaining every score and recommendation
- preserving provenance and decision history
- enforcing compliance before outreach or activation
- generating litigation-ready intelligence for attorney review

---

# Important Disclaimer

This repository is currently an MVP/prototype. Synthetic and demonstration data may be used. Illustrative scoring weights and confidence formulas are not outcome-calibrated, and the system is not legal advice.

Compliance, privacy, solicitation, DPPA, open-records, evidentiary, and professional-responsibility decisions must be reviewed and configured with qualified counsel before production use.

---

**Author:** Abraham Gilbert  
**License:** Proprietary MVP Prototype
