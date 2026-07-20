# G-CCI Formal Ontology Integration

Version: `gcci-ontology-v1.0.0`

The runtime now implements the ontology's highest-priority architectural invariants in TypeScript:

1. Event correlation, causal relationship, and party attribution are independent confidence measures.
2. Case-opportunity scoring does not imply contact eligibility.
3. Temporal observations preserve separate event, call, CAD, detection, arrival, record, source, ingestion, and effective times.
4. Intake evidence, temporal normalization, and scores are appended to a provenance-aware decision ledger.
5. Ledger entries are hash-linked and append-only at the service interface.
6. Every score records model lineage and the ledger entries from which it was derived.
7. Party attribution remains zero unless identity verification is explicitly supplied; it is never boosted by correlation or case value.

## Runtime endpoints

- `POST /api/intake` — intake + scoring + temporal normalization + ledger writes
- `GET /api/ontology` — ontology version and runtime invariants
- `GET /api/ledger/integrity` — verifies the in-memory hash chain
- `GET /api/ledger/subject/:subjectId` — complete subject history
- `GET /api/ledger/provenance/:entryId` — provenance chain for Explain This Decision

## Production migration

The current ledger remains process-local memory. Production should persist immutable entries in PostgreSQL or an event store, enforce append-only database permissions, use transactionally generated sequence/UUID identifiers, and anchor entry hashes externally where evidentiary requirements justify it.

The complete RDF/OWL/SHACL ontology package should live under this directory in a subsequent repository commit. The runtime TypeScript model is intentionally aligned with that formal ontology rather than duplicating an unrelated vocabulary.
