from __future__ import annotations

import asyncio
import logging
from datetime import timedelta

from sqlalchemy import or_, select

from .acquisition import ACQUISITION_PRIORITY_MODEL_VERSION, build_acquisition_tasks_for_score
from .config import settings
from .database import (
    DecisionLedgerRow,
    EventRow,
    HypothesisRevisionRow,
    ScoreJobRow,
    SessionLocal,
    utcnow,
)
from .ledger import append_ledger_entry
from .persistence_service import PersistentCorrelationService
from .repository import event_row_to_model
from .scoring_bridge import CanonicalScorerClient, next_retry_time, persist_score_result


log = logging.getLogger("gcci.correlation.worker")
service = PersistentCorrelationService()
scorer = CanonicalScorerClient()


async def fetch_pending_events(limit: int) -> list[EventRow]:
    async with SessionLocal() as session:
        rows = (
            await session.execute(
                select(EventRow)
                .where(
                    or_(
                        EventRow.correlation_processed_hash.is_(None),
                        EventRow.correlation_processed_hash != EventRow.raw_sha256,
                    )
                )
                .order_by(EventRow.last_ingested_at.asc())
                .limit(limit)
            )
        ).scalars().all()
        return list(rows)


async def process_event(event_row: EventRow) -> None:
    event = event_row_to_model(event_row)
    async with SessionLocal() as session:
        try:
            async with session.begin():
                hypothesis_ids = await service.correlate_event(session, event)
            log.info("processed event=%s hypotheses=%s", event.id, hypothesis_ids)
        except Exception:
            log.exception("correlation failed event=%s", event.id)
            raise


async def claim_score_jobs(limit: int) -> list[str]:
    """Claim ready jobs with a time-bounded PROCESSING lease."""
    now = utcnow()
    lease_until = now + timedelta(seconds=settings.canonical_scorer_timeout_seconds + 30)
    async with SessionLocal() as session:
        async with session.begin():
            rows = (
                await session.execute(
                    select(ScoreJobRow)
                    .where(
                        ScoreJobRow.next_attempt_at <= now,
                        ScoreJobRow.status.in_(["PENDING", "FAILED", "PROCESSING"]),
                    )
                    .order_by(ScoreJobRow.next_attempt_at.asc(), ScoreJobRow.created_at.asc())
                    .limit(limit)
                    .with_for_update(skip_locked=True)
                )
            ).scalars().all()
            ids: list[str] = []
            for row in rows:
                row.status = "PROCESSING"
                row.attempts += 1
                row.next_attempt_at = lease_until
                row.updated_at = now
                row.last_error = None
                ids.append(row.id)
            return ids


async def _score_request_ledger_id(session, job: ScoreJobRow) -> str | None:
    entries = (
        await session.execute(
            select(DecisionLedgerRow)
            .where(
                DecisionLedgerRow.subject_id == job.hypothesis_id,
                DecisionLedgerRow.entry_type == "ScoreRequest",
            )
            .order_by(DecisionLedgerRow.sequence_no.desc())
        )
    ).scalars().all()
    for entry in entries:
        if entry.payload_json.get("scoreJobId") == job.id:
            return entry.id
    return None


async def _revision_context(session, job: ScoreJobRow):
    revision = (
        await session.execute(
            select(HypothesisRevisionRow).where(
                HypothesisRevisionRow.hypothesis_id == job.hypothesis_id,
                HypothesisRevisionRow.revision == job.revision,
            )
        )
    ).scalar_one()
    member_ids = list(revision.member_event_ids_json)
    event_rows = []
    if member_ids:
        event_rows = (
            await session.execute(select(EventRow).where(EventRow.id.in_(member_ids)))
        ).scalars().all()
    events = [event_row_to_model(row) for row in event_rows]
    return revision, events


async def process_score_job(job_id: str) -> None:
    async with SessionLocal() as session:
        job = await session.get(ScoreJobRow, job_id)
        if job is None:
            return
        canonical_input = job.score_input_json["canonicalInput"]
        attempts = job.attempts

    try:
        response = await scorer.score(canonical_input)
    except Exception as exc:
        async with SessionLocal() as session:
            async with session.begin():
                job = (
                    await session.execute(
                        select(ScoreJobRow).where(ScoreJobRow.id == job_id).with_for_update()
                    )
                ).scalar_one_or_none()
                if job is None or job.status == "SUCCEEDED":
                    return
                job.status = "FAILED"
                job.last_error = str(exc)[:4000]
                job.next_attempt_at = next_retry_time(attempts)
                job.updated_at = utcnow()
        log.exception("canonical scoring failed job=%s", job_id)
        return

    async with SessionLocal() as session:
        async with session.begin():
            job = (
                await session.execute(
                    select(ScoreJobRow).where(ScoreJobRow.id == job_id).with_for_update()
                )
            ).scalar_one_or_none()
            if job is None or job.status == "SUCCEEDED":
                return

            score_result = await persist_score_result(session, job=job, response=response)
            request_ledger_id = await _score_request_ledger_id(session, job)
            previous_score_entry = (
                await session.execute(
                    select(DecisionLedgerRow)
                    .where(
                        DecisionLedgerRow.subject_id == job.hypothesis_id,
                        DecisionLedgerRow.entry_type == "Score",
                    )
                    .order_by(DecisionLedgerRow.sequence_no.desc())
                    .limit(1)
                )
            ).scalar_one_or_none()

            score_entry = await append_ledger_entry(
                session,
                entry_type="Score",
                subject_id=job.hypothesis_id,
                payload={
                    "action": "canonical-score-computed",
                    "hypothesisRevision": job.revision,
                    "scoreJobId": job.id,
                    "input": job.score_input_json,
                    "materiality": job.materiality_json,
                    "result": response.model_dump(mode="json"),
                    "scoreResultId": score_result.id,
                },
                produced_by="ai.canonicalScoreIntake",
                source_system="TypeScript:/api/scoring/score",
                model_version=response.result.modelVersion,
                input_entry_ids=[request_ledger_id] if request_ledger_id else [],
                supersedes_entry_id=previous_score_entry.id if previous_score_entry else None,
            )

            revision, events = await _revision_context(session, job)
            acquisition_tasks = await build_acquisition_tasks_for_score(
                session,
                score_result=score_result,
                hypothesis_payload=revision.payload_json,
                events=events,
            )
            for task in acquisition_tasks:
                await append_ledger_entry(
                    session,
                    entry_type="EvidenceAcquisitionPriority",
                    subject_id=job.hypothesis_id,
                    payload={
                        "action": "evidence-acquisition-ranked",
                        "hypothesisRevision": job.revision,
                        "taskId": task.id,
                        "evidenceType": task.evidence_type,
                        "expectedInformationGain": task.expected_information_gain,
                        "acquisitionPriorityScore": task.acquisition_priority_score,
                        "caseOpportunityScore": task.case_opportunity_score,
                        "tier": task.tier,
                        "status": task.status,
                        "recommendedAction": task.recommended_action,
                    },
                    produced_by="ai.evidenceAcquisitionPriority",
                    source_system="Python:acquisition.py",
                    model_version=ACQUISITION_PRIORITY_MODEL_VERSION,
                    input_entry_ids=[score_entry.id],
                )

            job.status = "SUCCEEDED"
            job.last_error = None
            job.updated_at = utcnow()
            job.next_attempt_at = utcnow()

    log.info(
        "scored hypothesis=%s revision=%s score=%.2f tier=%s",
        job.hypothesis_id,
        job.revision,
        response.result.score,
        response.result.tier,
    )


async def run_forever() -> None:
    logging.basicConfig(level=logging.INFO)
    log.info("starting G-CCI correlation + canonical scoring worker")

    while True:
        did_work = False

        rows = await fetch_pending_events(settings.worker_batch_size)
        for row in rows:
            did_work = True
            try:
                await process_event(row)
            except Exception:
                await asyncio.sleep(0.25)

        score_job_ids = await claim_score_jobs(settings.scoring_worker_batch_size)
        for job_id in score_job_ids:
            did_work = True
            await process_score_job(job_id)

        if not did_work:
            await asyncio.sleep(settings.worker_poll_seconds)


if __name__ == "__main__":
    asyncio.run(run_forever())
