from __future__ import annotations

from datetime import datetime, timezone

import pytest
from sqlalchemy import delete, select

from gcci.database import (
    DecisionLedgerRow,
    EventRow,
    HypothesisEventRow,
    HypothesisRevisionRow,
    HypothesisRow,
    SessionLocal,
)
from gcci.ledger import verify_ledger_chain
from gcci.models import GeoPoint, NormalizedEvent, Provenance, SourceKind
from gcci.persistence_service import PersistentCorrelationService


pytestmark = pytest.mark.integration


def make_event(event_id: str, source: str, minute: int, lat: float, lon: float) -> NormalizedEvent:
    return NormalizedEvent(
        id=event_id,
        source_kind=SourceKind.GDOT_511 if source == "GDOT" else SourceKind.GEMA_WAZE,
        observed_at=datetime(2026, 1, 1, 12, minute, tzinfo=timezone.utc),
        reported_at=datetime(2026, 1, 1, 12, minute, tzinfo=timezone.utc),
        point=GeoPoint(latitude=lat, longitude=lon),
        roadway="I-285",
        direction="WB",
        event_type="CRASH",
        description="Commercial box truck crash, EMS responding",
        commercial_vehicle_hint=True,
        injury_hint=True,
        provenance=Provenance(
            source_system=source,
            source_record_id=event_id,
            raw_sha256=f"hash-{event_id}",
        ),
    )


@pytest.fixture(autouse=True)
async def clean_database():
    async with SessionLocal() as session:
        async with session.begin():
            for table in (
                DecisionLedgerRow,
                HypothesisEventRow,
                HypothesisRevisionRow,
                HypothesisRow,
                EventRow,
            ):
                await session.execute(delete(table))
    yield


@pytest.mark.asyncio
async def test_new_source_record_revises_existing_incident_hypothesis():
    service = PersistentCorrelationService()
    first = make_event("gdot:1", "GDOT", 0, 33.91, -84.37)
    second = make_event("gema:2", "GEMA", 2, 33.9104, -84.3703)

    async with SessionLocal() as session:
        async with session.begin():
            first_hypotheses = await service.ingest_and_correlate(session, first)

    assert len(first_hypotheses) == 1
    hypothesis_id = first_hypotheses[0]

    async with SessionLocal() as session:
        async with session.begin():
            second_hypotheses = await service.ingest_and_correlate(session, second)

    assert hypothesis_id in second_hypotheses

    async with SessionLocal() as session:
        hypothesis = await session.get(HypothesisRow, hypothesis_id)
        assert hypothesis is not None
        assert hypothesis.current_revision == 2

        revisions = (
            await session.execute(
                select(HypothesisRevisionRow)
                .where(HypothesisRevisionRow.hypothesis_id == hypothesis_id)
                .order_by(HypothesisRevisionRow.revision)
            )
        ).scalars().all()
        assert len(revisions) == 2
        assert set(revisions[-1].member_event_ids_json) == {"gdot:1", "gema:2"}

        links = (
            await session.execute(
                select(HypothesisEventRow.event_id).where(
                    HypothesisEventRow.hypothesis_id == hypothesis_id
                )
            )
        ).scalars().all()
        assert set(links) == {"gdot:1", "gema:2"}

        valid, error = await verify_ledger_chain(session)
        assert valid, error

        hypothesis_entries = (
            await session.execute(
                select(DecisionLedgerRow).where(
                    DecisionLedgerRow.subject_id == hypothesis_id,
                    DecisionLedgerRow.entry_type == "Hypothesis",
                )
            )
        ).scalars().all()
        assert len(hypothesis_entries) == 2
        assert hypothesis_entries[-1].supersedes_entry_id == hypothesis_entries[0].id
