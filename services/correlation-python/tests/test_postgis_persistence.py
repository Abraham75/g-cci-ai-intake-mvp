from __future__ import annotations

from datetime import datetime, timezone

import pytest
from sqlalchemy import delete, select, text

from gcci.camera_repository import camera_candidates_for_hypothesis, upsert_camera_inventory
from gcci.database import (
    DecisionLedgerRow,
    EvidenceAcquisitionTaskRow,
    EventRow,
    HypothesisEventRow,
    HypothesisRevisionRow,
    HypothesisRow,
    ScoreJobRow,
    ScoreResultRow,
    SessionLocal,
)
from gcci.ledger import verify_ledger_chain
from gcci.models import Camera, GeoPoint, NormalizedEvent, Provenance, SourceKind
from gcci.persistence_service import PersistentCorrelationService
from gcci.worker import claim_score_jobs, process_score_job


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


def make_camera(camera_id: str, lat: float, lon: float, direction: str = "WB") -> Camera:
    return Camera(
        id=camera_id,
        name=f"Camera {camera_id}",
        point=GeoPoint(latitude=lat, longitude=lon),
        roadway="I-285",
        direction=direction,
        snapshot_url=f"https://example.invalid/{camera_id}.jpg",
        source_system="TEST_GDOT_CAMERA",
        provenance=Provenance(
            source_system="TEST_GDOT_CAMERA",
            source_record_id=camera_id,
            raw_sha256=f"camera-hash-{camera_id}",
        ),
    )


@pytest.fixture(autouse=True)
async def clean_database():
    async with SessionLocal() as session:
        async with session.begin():
            # Camera inventory is implemented with SQL rather than ORM rows; clear it
            # explicitly so integration tests remain order-independent.
            await session.execute(text("DELETE FROM hypothesis_camera_candidates"))
            await session.execute(text("DELETE FROM traffic_cameras"))
            for table in (
                DecisionLedgerRow,
                EvidenceAcquisitionTaskRow,
                ScoreResultRow,
                ScoreJobRow,
                HypothesisEventRow,
                HypothesisRevisionRow,
                HypothesisRow,
                EventRow,
            ):
                await session.execute(delete(table))
    yield


async def _create_two_revision_hypothesis() -> str:
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
    return hypothesis_id


@pytest.mark.asyncio
async def test_new_source_record_revises_existing_incident_hypothesis_and_queues_scores():
    hypothesis_id = await _create_two_revision_hypothesis()

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
                    HypothesisEventRow.hypothesis_id == hypothesis_id,
                    HypothesisEventRow.active.is_(True),
                )
            )
        ).scalars().all()
        assert set(links) == {"gdot:1", "gema:2"}

        score_jobs = (
            await session.execute(
                select(ScoreJobRow)
                .where(ScoreJobRow.hypothesis_id == hypothesis_id)
                .order_by(ScoreJobRow.revision)
            )
        ).scalars().all()
        assert [job.revision for job in score_jobs] == [1, 2]
        assert all(job.status == "PENDING" for job in score_jobs)
        assert score_jobs[1].materiality_json["material"] is True
        assert "supporting evidence membership changed" in score_jobs[1].materiality_json["reasons"]

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

        score_requests = (
            await session.execute(
                select(DecisionLedgerRow).where(
                    DecisionLedgerRow.subject_id == hypothesis_id,
                    DecisionLedgerRow.entry_type == "ScoreRequest",
                )
            )
        ).scalars().all()
        assert len(score_requests) == 2


@pytest.mark.asyncio
async def test_camera_inventory_is_spatially_ranked_and_revision_scoped():
    async with SessionLocal() as session:
        async with session.begin():
            count = await upsert_camera_inventory(
                session,
                [
                    make_camera("cam-near", 33.9102, -84.3701, "WB"),
                    make_camera("cam-opposite", 33.9103, -84.3702, "EB"),
                    make_camera("cam-far", 34.10, -84.60, "WB"),
                ],
                produced_by="test.camera-seed",
            )
            assert count == 3

    hypothesis_id = await _create_two_revision_hypothesis()

    async with SessionLocal() as session:
        candidates = await camera_candidates_for_hypothesis(session, hypothesis_id)
        assert candidates
        assert all(candidate["revision"] == 2 for candidate in candidates)
        assert candidates[0]["cameraId"] == "cam-near"
        assert candidates[0]["roadwayMatch"] is True
        assert candidates[0]["directionMatch"] is True
        assert candidates[0]["relevanceScore"] > candidates[1]["relevanceScore"]
        assert all(candidate["cameraId"] != "cam-far" for candidate in candidates)
        assert candidates[0]["preservationWindowStart"] < candidates[0]["preservationWindowEnd"]

        lifecycle = (
            await session.execute(
                text(
                    """
                    SELECT revision, status, count(*) AS n
                    FROM hypothesis_camera_candidates
                    WHERE hypothesis_id = :hypothesis_id
                    GROUP BY revision, status
                    ORDER BY revision
                    """
                ),
                {"hypothesis_id": hypothesis_id},
            )
        ).mappings().all()
        assert any(row["revision"] == 1 and row["status"] == "SUPERSEDED" for row in lifecycle)
        assert any(row["revision"] == 2 and row["status"] == "CURRENT" for row in lifecycle)

        camera_entries = (
            await session.execute(
                select(DecisionLedgerRow).where(
                    DecisionLedgerRow.subject_id == hypothesis_id,
                    DecisionLedgerRow.entry_type == "CameraCandidateSet",
                )
            )
        ).scalars().all()
        assert len(camera_entries) == 2
        assert all(entry.input_entry_ids_json for entry in camera_entries)

        valid, error = await verify_ledger_chain(session)
        assert valid, error


@pytest.mark.asyncio
async def test_material_revisions_are_scored_and_create_current_acquisition_queue():
    hypothesis_id = await _create_two_revision_hypothesis()

    claimed = await claim_score_jobs(10)
    assert len(claimed) == 2
    for job_id in claimed:
        await process_score_job(job_id)

    async with SessionLocal() as session:
        jobs = (
            await session.execute(
                select(ScoreJobRow)
                .where(ScoreJobRow.hypothesis_id == hypothesis_id)
                .order_by(ScoreJobRow.revision)
            )
        ).scalars().all()
        assert [job.status for job in jobs] == ["SUCCEEDED", "SUCCEEDED"]

        results = (
            await session.execute(
                select(ScoreResultRow)
                .where(ScoreResultRow.hypothesis_id == hypothesis_id)
                .order_by(ScoreResultRow.revision)
            )
        ).scalars().all()
        assert [row.revision for row in results] == [1, 2]
        assert all(0 <= row.score <= 1 for row in results)
        assert all(row.tier in {"A", "B", "C", "D"} for row in results)
        assert all(row.model_version == "gcci-cos-v1.0-consolidated-ts-port" for row in results)

        tasks = (
            await session.execute(
                select(EvidenceAcquisitionTaskRow)
                .where(EvidenceAcquisitionTaskRow.hypothesis_id == hypothesis_id)
                .order_by(
                    EvidenceAcquisitionTaskRow.revision,
                    EvidenceAcquisitionTaskRow.acquisition_priority_score.desc(),
                )
            )
        ).scalars().all()
        assert tasks
        revision_one = [task for task in tasks if task.revision == 1]
        revision_two = [task for task in tasks if task.revision == 2]
        assert revision_one and revision_two
        assert all(task.status == "SUPERSEDED" for task in revision_one)
        assert all(task.status == "OPEN" for task in revision_two)
        assert all(0 <= task.acquisition_priority_score <= 1 for task in tasks)
        assert revision_two == sorted(
            revision_two,
            key=lambda task: task.acquisition_priority_score,
            reverse=True,
        )

        score_entries = (
            await session.execute(
                select(DecisionLedgerRow)
                .where(
                    DecisionLedgerRow.subject_id == hypothesis_id,
                    DecisionLedgerRow.entry_type == "Score",
                )
                .order_by(DecisionLedgerRow.sequence_no)
            )
        ).scalars().all()
        assert len(score_entries) == 2
        assert score_entries[-1].supersedes_entry_id == score_entries[0].id
        assert score_entries[-1].input_entry_ids_json

        acquisition_entries = (
            await session.execute(
                select(DecisionLedgerRow).where(
                    DecisionLedgerRow.subject_id == hypothesis_id,
                    DecisionLedgerRow.entry_type == "EvidenceAcquisitionPriority",
                )
            )
        ).scalars().all()
        assert acquisition_entries
        assert all(entry.input_entry_ids_json for entry in acquisition_entries)

        valid, error = await verify_ledger_chain(session)
        assert valid, error
