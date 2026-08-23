from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .config import Settings, settings
from .correlation import build_incident_hypotheses
from .database import DecisionLedgerRow, EventRow, utcnow
from .ledger import append_ledger_entry
from .models import NormalizedEvent
from .repository import (
    candidate_events_for,
    event_row_to_model,
    persist_hypothesis_revision,
    upsert_event,
)


async def _latest_evidence_ledger_id(session: AsyncSession, event_id: str) -> str | None:
    row = (
        await session.execute(
            select(DecisionLedgerRow)
            .where(
                DecisionLedgerRow.subject_id == event_id,
                DecisionLedgerRow.entry_type == "Evidence",
            )
            .order_by(DecisionLedgerRow.sequence_no.desc())
            .limit(1)
        )
    ).scalar_one_or_none()
    return row.id if row else None


class PersistentCorrelationService:
    def __init__(self, cfg: Settings = settings):
        self.cfg = cfg

    async def ingest_event(self, session: AsyncSession, event: NormalizedEvent) -> EventRow:
        row, is_new = await upsert_event(session, event)
        evidence_entry = await append_ledger_entry(
            session,
            entry_type="Evidence",
            subject_id=event.id,
            payload={
                "action": "event-ingested" if is_new else "event-refreshed",
                "event": event.model_dump(mode="json"),
            },
            produced_by="correlation.ingestion",
            source_system=event.provenance.source_system,
        )
        await session.flush()
        return row

    async def correlate_event(self, session: AsyncSession, event: NormalizedEvent) -> list[str]:
        candidate_rows = await candidate_events_for(session, event, self.cfg)
        cluster_events = [event] + [event_row_to_model(row) for row in candidate_rows]
        hypotheses, _ = build_incident_hypotheses(cluster_events, self.cfg)

        persisted_ids: list[str] = []
        for hypothesis in hypotheses:
            if event.id not in hypothesis.member_event_ids:
                continue

            hypothesis_row, revision_row, created, newly_linked = await persist_hypothesis_revision(
                session, hypothesis
            )

            evidence_entry_ids = [
                ledger_id
                for member_id in hypothesis.member_event_ids
                if (ledger_id := await _latest_evidence_ledger_id(session, member_id)) is not None
            ]

            previous_revision_entry = (
                await session.execute(
                    select(DecisionLedgerRow)
                    .where(
                        DecisionLedgerRow.subject_id == hypothesis_row.id,
                        DecisionLedgerRow.entry_type == "Hypothesis",
                    )
                    .order_by(DecisionLedgerRow.sequence_no.desc())
                    .limit(1)
                )
            ).scalar_one_or_none()

            ledger_entry = await append_ledger_entry(
                session,
                entry_type="Hypothesis",
                subject_id=hypothesis_row.id,
                payload={
                    "action": "hypothesis-created" if created else "hypothesis-revised",
                    "revision": revision_row.revision,
                    "newly_linked_event_ids": newly_linked,
                    "hypothesis": revision_row.payload_json,
                },
                produced_by="correlation.hypothesisEngine",
                source_system="PostgreSQL/PostGIS",
                model_version=hypothesis.model_version,
                input_entry_ids=evidence_entry_ids,
                supersedes_entry_id=previous_revision_entry.id if previous_revision_entry else None,
            )

            for event_id in newly_linked:
                await append_ledger_entry(
                    session,
                    entry_type="Assertion",
                    subject_id=hypothesis_row.id,
                    payload={
                        "action": "supporting-evidence-linked",
                        "hypothesis_revision": revision_row.revision,
                        "event_id": event_id,
                    },
                    produced_by="correlation.hypothesisEngine",
                    source_system="PostgreSQL/PostGIS",
                    model_version=hypothesis.model_version,
                    input_entry_ids=[ledger_entry.id],
                )

            persisted_ids.append(hypothesis_row.id)

        row = await session.get(EventRow, event.id)
        if row is not None:
            row.correlation_processed_hash = row.raw_sha256
            row.correlation_processed_at = utcnow()
        await session.flush()
        return persisted_ids

    async def ingest_and_correlate(self, session: AsyncSession, event: NormalizedEvent) -> list[str]:
        await self.ingest_event(session, event)
        return await self.correlate_event(session, event)
