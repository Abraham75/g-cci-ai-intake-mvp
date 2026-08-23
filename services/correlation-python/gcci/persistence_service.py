from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .config import Settings, settings
from .correlation import build_incident_hypotheses
from .database import DecisionLedgerRow, EventRow, utcnow
from .ledger import append_ledger_entry
from .models import IncidentHypothesis, NormalizedEvent
from .repository import (
    candidate_events_for,
    event_row_to_model,
    events_for_hypothesis,
    find_matching_hypothesis,
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


def _choose_hypothesis_for_event(
    hypotheses: list[IncidentHypothesis], event_id: str
) -> IncidentHypothesis | None:
    matches = [h for h in hypotheses if event_id in h.member_event_ids]
    if not matches:
        return None
    return max(matches, key=lambda h: (len(h.member_event_ids), h.machine_confidence))


class PersistentCorrelationService:
    def __init__(self, cfg: Settings = settings):
        self.cfg = cfg

    async def ingest_event(
        self, session: AsyncSession, event: NormalizedEvent
    ) -> tuple[EventRow, bool]:
        row, is_new, changed = await upsert_event(session, event)
        needs_processing = changed or row.correlation_processed_hash != row.raw_sha256

        if changed:
            await append_ledger_entry(
                session,
                entry_type="Evidence",
                subject_id=event.id,
                payload={
                    "action": "event-ingested" if is_new else "event-revised",
                    "event": event.model_dump(mode="json"),
                    "rawSha256": row.raw_sha256,
                },
                produced_by="correlation.ingestion",
                source_system=event.provenance.source_system,
            )
            await session.flush()

        return row, needs_processing

    async def correlate_event(self, session: AsyncSession, event: NormalizedEvent) -> list[str]:
        candidate_rows = await candidate_events_for(session, event, self.cfg)
        local_events = [event] + [event_row_to_model(row) for row in candidate_rows]
        local_hypotheses, _ = build_incident_hypotheses(local_events, self.cfg)
        seed = _choose_hypothesis_for_event(local_hypotheses, event.id)

        if seed is None:
            row = await session.get(EventRow, event.id)
            if row is not None:
                row.correlation_processed_hash = row.raw_sha256
                row.correlation_processed_at = utcnow()
            await session.flush()
            return []

        existing = await find_matching_hypothesis(session, seed, self.cfg)
        if existing is not None:
            accumulated_rows = await events_for_hypothesis(session, existing.id)
            by_id = {item.id: item for item in local_events}
            for row in accumulated_rows:
                model = event_row_to_model(row)
                by_id[model.id] = model

            rebuilt, _ = build_incident_hypotheses(list(by_id.values()), self.cfg)
            full_hypothesis = _choose_hypothesis_for_event(rebuilt, event.id)
            if full_hypothesis is not None:
                seed = full_hypothesis

        hypothesis_row, revision_row, created, newly_linked, removed_links = (
            await persist_hypothesis_revision(session, seed)
        )

        evidence_entry_ids = [
            ledger_id
            for member_id in seed.member_event_ids
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
                "newlyLinkedEventIds": newly_linked,
                "removedEventIds": removed_links,
                "hypothesis": revision_row.payload_json,
            },
            produced_by="correlation.hypothesisEngine",
            source_system="PostgreSQL/PostGIS",
            model_version=seed.model_version,
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
                    "hypothesisRevision": revision_row.revision,
                    "eventId": event_id,
                },
                produced_by="correlation.hypothesisEngine",
                source_system="PostgreSQL/PostGIS",
                model_version=seed.model_version,
                input_entry_ids=[ledger_entry.id],
            )

        for event_id in removed_links:
            await append_ledger_entry(
                session,
                entry_type="Assertion",
                subject_id=hypothesis_row.id,
                payload={
                    "action": "supporting-evidence-withdrawn",
                    "hypothesisRevision": revision_row.revision,
                    "eventId": event_id,
                },
                produced_by="correlation.hypothesisEngine",
                source_system="PostgreSQL/PostGIS",
                model_version=seed.model_version,
                input_entry_ids=[ledger_entry.id],
            )

        row = await session.get(EventRow, event.id)
        if row is not None:
            row.correlation_processed_hash = row.raw_sha256
            row.correlation_processed_at = utcnow()
        await session.flush()
        return [hypothesis_row.id]

    async def ingest_and_correlate(self, session: AsyncSession, event: NormalizedEvent) -> list[str]:
        _, needs_processing = await self.ingest_event(session, event)
        if not needs_processing:
            return []
        return await self.correlate_event(session, event)
