from __future__ import annotations

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select

from .database import HypothesisRevisionRow, HypothesisRow, SessionLocal
from .ledger import ledger_entries_for_subject, verify_ledger_chain
from .models import Camera, CorrelatedIncidentPackage, NormalizedEvent
from .persistence_service import PersistentCorrelationService
from .service import CrossSourceCorrelationService

app = FastAPI(
    title="G-CCI Cross-Source Event Correlation Service",
    version="1.1.0",
    description=(
        "Correlates transportation-event records across independent sources, persists "
        "normalized events and versioned incident hypotheses in PostgreSQL/PostGIS, "
        "discovers nearby cameras, ranks evidence gaps, and writes revisions into an "
        "append-only decision ledger. It does not identify people or authorize outreach."
    ),
)

analysis_service = CrossSourceCorrelationService()
persistence_service = PersistentCorrelationService()


class CorrelateRequest(BaseModel):
    events: list[NormalizedEvent] = Field(min_length=1)
    cameras: list[Camera] = Field(default_factory=list)


class CorrelateResponse(BaseModel):
    packages: list[CorrelatedIncidentPackage]
    policy: dict[str, object]


class IngestResponse(BaseModel):
    event_id: str
    hypothesis_ids: list[str]
    persisted: bool = True


class BatchIngestRequest(BaseModel):
    events: list[NormalizedEvent] = Field(min_length=1, max_length=5000)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "gcci-cross-source-correlation", "version": "1.1.0"}


@app.post("/correlate", response_model=CorrelateResponse)
def correlate(body: CorrelateRequest) -> CorrelateResponse:
    packages = analysis_service.analyze(body.events, body.cameras)
    return CorrelateResponse(
        packages=packages,
        policy={
            "personIdentification": False,
            "partyAttributionPerformed": False,
            "contactEligibilityEvaluated": False,
            "requiresComplianceGateBeforeOutreach": True,
        },
    )


@app.post("/events/ingest", response_model=IngestResponse)
async def ingest_event(event: NormalizedEvent) -> IngestResponse:
    async with SessionLocal() as session:
        async with session.begin():
            hypothesis_ids = await persistence_service.ingest_and_correlate(session, event)
    return IngestResponse(event_id=event.id, hypothesis_ids=hypothesis_ids)


@app.post("/events/ingest-batch", response_model=list[IngestResponse])
async def ingest_batch(body: BatchIngestRequest) -> list[IngestResponse]:
    results: list[IngestResponse] = []
    # One transaction per event prevents one malformed/rejected record from rolling back a full feed batch.
    for event in body.events:
        async with SessionLocal() as session:
            async with session.begin():
                hypothesis_ids = await persistence_service.ingest_and_correlate(session, event)
        results.append(IngestResponse(event_id=event.id, hypothesis_ids=hypothesis_ids))
    return results


@app.get("/hypotheses/{hypothesis_id}")
async def get_hypothesis(hypothesis_id: str) -> dict:
    async with SessionLocal() as session:
        hypothesis = await session.get(HypothesisRow, hypothesis_id)
        if hypothesis is None:
            raise HTTPException(404, "Unknown hypothesis")
        revision = (
            await session.execute(
                select(HypothesisRevisionRow)
                .where(
                    HypothesisRevisionRow.hypothesis_id == hypothesis_id,
                    HypothesisRevisionRow.revision == hypothesis.current_revision,
                )
                .limit(1)
            )
        ).scalar_one()
        return revision.payload_json


@app.get("/hypotheses/{hypothesis_id}/revisions")
async def get_hypothesis_revisions(hypothesis_id: str) -> list[dict]:
    async with SessionLocal() as session:
        rows = (
            await session.execute(
                select(HypothesisRevisionRow)
                .where(HypothesisRevisionRow.hypothesis_id == hypothesis_id)
                .order_by(HypothesisRevisionRow.revision)
            )
        ).scalars().all()
        if not rows:
            raise HTTPException(404, "Unknown hypothesis")
        return [row.payload_json for row in rows]


@app.get("/ledger/subject/{subject_id}")
async def get_subject_ledger(subject_id: str) -> list[dict]:
    async with SessionLocal() as session:
        rows = await ledger_entries_for_subject(session, subject_id)
        return [
            {
                "sequenceNo": row.sequence_no,
                "id": row.id,
                "entryType": row.entry_type,
                "subjectId": row.subject_id,
                "payload": row.payload_json,
                "producedBy": row.produced_by,
                "inputEntryIds": row.input_entry_ids_json,
                "supersedesEntryId": row.supersedes_entry_id,
                "previousHash": row.previous_hash,
                "entryHash": row.entry_hash,
                "createdAt": row.created_at.isoformat(),
            }
            for row in rows
        ]


@app.get("/ledger/integrity")
async def ledger_integrity() -> dict[str, object]:
    async with SessionLocal() as session:
        valid, error = await verify_ledger_chain(session)
    return {"valid": valid, "error": error}
