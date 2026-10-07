from __future__ import annotations

from datetime import datetime
from statistics import median
from uuid import uuid4

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import text

from .database import SessionLocal
from .ledger import append_ledger_entry
from .product_validation import (
    RankedLabel,
    investigation_yield,
    precision_at_k,
    qualification_precision,
)


router = APIRouter(tags=["product-validation"])

DISPOSITIONS = {
    "GOOD_CASE", "BAD_CASE", "NEEDS_MORE_INFORMATION", "DUPLICATE",
    "NOT_A_TRUCK_CASE", "INSUFFICIENT_INJURY", "LIABILITY_TOO_WEAK",
    "NO_COLLECTIBLE_DEFENDANT", "ALREADY_REPRESENTED", "OTHER",
}
OUTCOME_STAGES = {"INVESTIGATED", "ADVANCED", "SIGNED", "DECLINED", "REFERRED", "LOST", "SETTLED"}


class AttorneyReviewInput(BaseModel):
    disposition: str
    attorney_worthy: bool | None = None
    reason_code: str | None = Field(default=None, max_length=80)
    note: str | None = Field(default=None, max_length=4000)
    reviewed_by: str = Field(min_length=1, max_length=255)


class BenchmarkCaseInput(BaseModel):
    external_reference: str = Field(min_length=1, max_length=255)
    source: str = Field(min_length=1, max_length=255)
    occurred_at: datetime
    roadway: str | None = Field(default=None, max_length=255)
    known_valuable: bool
    traditional_awareness_at: datetime | None = None
    note: str | None = Field(default=None, max_length=4000)
    created_by: str = Field(min_length=1, max_length=255)


class BenchmarkMatchInput(BaseModel):
    hypothesis_id: str = Field(min_length=1, max_length=64)
    match_evidence: str = Field(min_length=1, max_length=4000)
    matched_by: str = Field(min_length=1, max_length=255)


class OutcomeInput(BaseModel):
    stage: str
    traditional_awareness_at: datetime | None = None
    note: str | None = Field(default=None, max_length=4000)
    recorded_by: str = Field(min_length=1, max_length=255)


@router.get("/opportunities")
async def opportunities(limit: int = Query(default=25, ge=1, le=200)) -> list[dict]:
    async with SessionLocal() as session:
        rows = (await session.execute(text("""
            WITH latest_score AS (
                SELECT DISTINCT ON (hypothesis_id)
                    hypothesis_id, revision, score, tier, scored_at
                FROM score_results
                ORDER BY hypothesis_id, revision DESC
            ),
            latest_review AS (
                SELECT DISTINCT ON (hypothesis_id)
                    hypothesis_id, disposition, attorney_worthy, created_at
                FROM attorney_case_reviews
                ORDER BY hypothesis_id, created_at DESC
            ),
            next_task AS (
                SELECT DISTINCT ON (hypothesis_id)
                    hypothesis_id, recommended_action, evidence_type,
                    acquisition_priority_score
                FROM evidence_acquisition_tasks
                WHERE status = 'OPEN'
                ORDER BY hypothesis_id, acquisition_priority_score DESC
            )
            SELECT h.id, h.current_revision, h.roadway, h.direction,
                   h.start_time, h.end_time, s.revision AS score_revision,
                   s.score, s.tier, s.scored_at,
                   r.disposition, r.attorney_worthy,
                   t.recommended_action, t.evidence_type,
                   t.acquisition_priority_score
            FROM incident_hypotheses h
            JOIN latest_score s ON s.hypothesis_id = h.id
            LEFT JOIN latest_review r ON r.hypothesis_id = h.id
            LEFT JOIN next_task t ON t.hypothesis_id = h.id
            WHERE h.active = true
            ORDER BY
                CASE s.tier WHEN 'A' THEN 1 WHEN 'B' THEN 2 WHEN 'C' THEN 3 ELSE 4 END,
                s.score DESC,
                s.scored_at DESC
            LIMIT :limit
        """), {"limit": limit})).mappings().all()
    return [{
        "hypothesisId": row["id"],
        "currentRevision": row["current_revision"],
        "scoreRevision": row["score_revision"],
        "score": float(row["score"]),
        "tier": row["tier"],
        "roadway": row["roadway"],
        "direction": row["direction"],
        "startTime": row["start_time"].isoformat(),
        "endTime": row["end_time"].isoformat(),
        "scoredAt": row["scored_at"].isoformat(),
        "attorneyReview": {
            "disposition": row["disposition"],
            "attorneyWorthy": row["attorney_worthy"],
        } if row["disposition"] else None,
        "nextBestAction": {
            "evidenceType": row["evidence_type"],
            "recommendedAction": row["recommended_action"],
            "priority": float(row["acquisition_priority_score"]),
        } if row["recommended_action"] else None,
    } for row in rows]


@router.post("/hypotheses/{hypothesis_id}/attorney-review")
async def record_attorney_review(hypothesis_id: str, body: AttorneyReviewInput) -> dict:
    if body.disposition not in DISPOSITIONS:
        raise HTTPException(422, "Unsupported attorney disposition")
    async with SessionLocal() as session:
        async with session.begin():
            hypothesis = (await session.execute(text(
                "SELECT current_revision FROM incident_hypotheses WHERE id=:id"
            ), {"id": hypothesis_id})).mappings().first()
            if hypothesis is None:
                raise HTTPException(404, "Unknown hypothesis")
            score = (await session.execute(text("""
                SELECT revision FROM score_results
                WHERE hypothesis_id=:id ORDER BY revision DESC LIMIT 1
            """), {"id": hypothesis_id})).mappings().first()
            review_id = str(uuid4())
            await session.execute(text("""
                INSERT INTO attorney_case_reviews
                    (id,hypothesis_id,score_revision,disposition,attorney_worthy,
                     reason_code,note,reviewed_by)
                VALUES
                    (:id,:hypothesis_id,:score_revision,:disposition,:attorney_worthy,
                     :reason_code,:note,:reviewed_by)
            """), {
                "id": review_id, "hypothesis_id": hypothesis_id,
                "score_revision": score["revision"] if score else None,
                "disposition": body.disposition, "attorney_worthy": body.attorney_worthy,
                "reason_code": body.reason_code, "note": body.note,
                "reviewed_by": body.reviewed_by,
            })
            entry = await append_ledger_entry(
                session, entry_type="AttorneyCaseReview", subject_id=hypothesis_id,
                payload={"reviewId": review_id, "disposition": body.disposition,
                         "attorneyWorthy": body.attorney_worthy,
                         "reasonCode": body.reason_code,
                         "hypothesisRevision": hypothesis["current_revision"],
                         "scoreRevision": score["revision"] if score else None},
                produced_by=body.reviewed_by, source_system="GCCI:AttorneyFeedback",
            )
    return {"id": review_id, "ledgerEntryId": entry.id, "recorded": True}


@router.get("/hypotheses/{hypothesis_id}/attorney-reviews")
async def attorney_reviews(hypothesis_id: str) -> list[dict]:
    async with SessionLocal() as session:
        rows = (await session.execute(text("""
            SELECT id, score_revision, disposition, attorney_worthy, reason_code,
                   note, reviewed_by, created_at
            FROM attorney_case_reviews WHERE hypothesis_id=:id
            ORDER BY created_at DESC
        """), {"id": hypothesis_id})).mappings().all()
    return [dict(row) | {"created_at": row["created_at"].isoformat()} for row in rows]


@router.post("/hypotheses/{hypothesis_id}/outcomes")
async def record_outcome(hypothesis_id: str, body: OutcomeInput) -> dict:
    if body.stage not in OUTCOME_STAGES:
        raise HTTPException(422, "Unsupported outcome stage")
    async with SessionLocal() as session:
        async with session.begin():
            exists = (await session.execute(text(
                "SELECT 1 FROM incident_hypotheses WHERE id=:id"
            ), {"id": hypothesis_id})).first()
            if not exists:
                raise HTTPException(404, "Unknown hypothesis")
            outcome_id = str(uuid4())
            await session.execute(text("""
                INSERT INTO case_outcomes
                    (id,hypothesis_id,stage,traditional_awareness_at,note,recorded_by)
                VALUES (:id,:hypothesis_id,:stage,:traditional_awareness_at,:note,:recorded_by)
            """), {
                "id": outcome_id, "hypothesis_id": hypothesis_id, "stage": body.stage,
                "traditional_awareness_at": body.traditional_awareness_at,
                "note": body.note, "recorded_by": body.recorded_by,
            })
            entry = await append_ledger_entry(
                session, entry_type="CaseOutcome", subject_id=hypothesis_id,
                payload={"outcomeId": outcome_id, "stage": body.stage,
                         "traditionalAwarenessAt": (
                             body.traditional_awareness_at.isoformat()
                             if body.traditional_awareness_at else None
                         )},
                produced_by=body.recorded_by, source_system="GCCI:OutcomeFeedback",
            )
    return {"id": outcome_id, "ledgerEntryId": entry.id, "recorded": True}


@router.post("/validation/benchmark-cases")
async def add_benchmark_case(body: BenchmarkCaseInput) -> dict:
    benchmark_id = str(uuid4())
    async with SessionLocal() as session:
        async with session.begin():
            try:
                await session.execute(text("""
                    INSERT INTO validation_benchmark_cases
                        (id,external_reference,source,occurred_at,roadway,known_valuable,
                         traditional_awareness_at,note,created_by)
                    VALUES
                        (:id,:external_reference,:source,:occurred_at,:roadway,:known_valuable,
                         :traditional_awareness_at,:note,:created_by)
                """), {
                    "id": benchmark_id, "external_reference": body.external_reference,
                    "source": body.source, "occurred_at": body.occurred_at,
                    "roadway": body.roadway, "known_valuable": body.known_valuable,
                    "traditional_awareness_at": body.traditional_awareness_at,
                    "note": body.note, "created_by": body.created_by,
                })
            except Exception as exc:
                raise HTTPException(409, "Benchmark external reference already exists") from exc
    return {"id": benchmark_id, "created": True}


@router.post("/validation/benchmark-cases/{benchmark_id}/match")
async def match_benchmark_case(benchmark_id: str, body: BenchmarkMatchInput) -> dict:
    async with SessionLocal() as session:
        async with session.begin():
            hypothesis = (await session.execute(text(
                "SELECT 1 FROM incident_hypotheses WHERE id=:id"
            ), {"id": body.hypothesis_id})).first()
            if not hypothesis:
                raise HTTPException(404, "Unknown hypothesis")
            result = await session.execute(text("""
                UPDATE validation_benchmark_cases
                SET matched_hypothesis_id=:hypothesis_id,
                    match_evidence=:match_evidence, matched_at=now()
                WHERE id=:id
                RETURNING external_reference
            """), {"id": benchmark_id, "hypothesis_id": body.hypothesis_id,
                    "match_evidence": body.match_evidence})
            row = result.mappings().first()
            if row is None:
                raise HTTPException(404, "Unknown benchmark case")
            entry = await append_ledger_entry(
                session, entry_type="ValidationBenchmarkMatch",
                subject_id=body.hypothesis_id,
                payload={"benchmarkId": benchmark_id,
                         "externalReference": row["external_reference"],
                         "matchEvidence": body.match_evidence},
                produced_by=body.matched_by, source_system="GCCI:ValidationCorpus",
            )
    return {"matched": True, "ledgerEntryId": entry.id}


@router.get("/validation/benchmark-cases")
async def benchmark_cases() -> list[dict]:
    async with SessionLocal() as session:
        rows = (await session.execute(text("""
            SELECT id, external_reference, source, occurred_at, roadway, known_valuable,
                   traditional_awareness_at, matched_hypothesis_id, match_evidence,
                   note, created_by, created_at, matched_at
            FROM validation_benchmark_cases ORDER BY occurred_at DESC
        """))).mappings().all()
    return [{
        "id": row["id"], "externalReference": row["external_reference"],
        "source": row["source"], "occurredAt": row["occurred_at"].isoformat(),
        "roadway": row["roadway"], "knownValuable": row["known_valuable"],
        "traditionalAwarenessAt": (
            row["traditional_awareness_at"].isoformat()
            if row["traditional_awareness_at"]
            else None
        ),
        "matchedHypothesisId": row["matched_hypothesis_id"],
        "matchEvidence": row["match_evidence"], "note": row["note"],
        "createdBy": row["created_by"], "createdAt": row["created_at"].isoformat(),
        "matchedAt": row["matched_at"].isoformat() if row["matched_at"] else None,
    } for row in rows]


@router.get("/validation/metrics")
async def validation_metrics(k: int = Query(default=10, ge=1, le=100)) -> dict:
    async with SessionLocal() as session:
        labels = (await session.execute(text("""
            WITH latest_score AS (
                SELECT DISTINCT ON (hypothesis_id) hypothesis_id, score
                FROM score_results ORDER BY hypothesis_id, revision DESC
            ),
            latest_review AS (
                SELECT DISTINCT ON (hypothesis_id) hypothesis_id, attorney_worthy
                FROM attorney_case_reviews ORDER BY hypothesis_id, created_at DESC
            )
            SELECT s.hypothesis_id, s.score, r.attorney_worthy
            FROM latest_score s LEFT JOIN latest_review r USING (hypothesis_id)
        """))).mappings().all()
        stages = (await session.execute(text("""
            SELECT DISTINCT ON (hypothesis_id) hypothesis_id, stage
            FROM case_outcomes ORDER BY hypothesis_id, created_at DESC
        """))).mappings().all()
        benchmark = (await session.execute(text("""
            SELECT b.known_valuable, b.matched_hypothesis_id,
                   b.traditional_awareness_at, h.created_at AS gcci_detected_at
            FROM validation_benchmark_cases b
            LEFT JOIN incident_hypotheses h ON h.id=b.matched_hypothesis_id
        """))).mappings().all()

    ranked = [RankedLabel(row["hypothesis_id"], float(row["score"]), row["attorney_worthy"])
              for row in labels]
    valuable_benchmarks = [row for row in benchmark if row["known_valuable"]]
    matched_valuable = [row for row in valuable_benchmarks if row["matched_hypothesis_id"]]
    discovery_recall = (
        len(matched_valuable) / len(valuable_benchmarks)
        if valuable_benchmarks else None
    )
    benchmark_timing = [
        row for row in matched_valuable
        if row["traditional_awareness_at"] and row["gcci_detected_at"]
    ]
    time_advantages = [
        (row["gcci_detected_at"] - row["traditional_awareness_at"]).total_seconds() / 3600
        for row in benchmark_timing
    ]
    reviewed_count = sum(1 for row in ranked if row.attorney_worthy is not None)
    return {
        "discoveryRecall": discovery_recall,
        "precisionAtK": precision_at_k(ranked, k),
        "k": k,
        "qualificationPrecision": qualification_precision(ranked),
        "investigationYield": investigation_yield([row["stage"] for row in stages]),
        "medianTimeAdvantageHours": (
            median(time_advantages) if time_advantages else None
        ),
        "counts": {
            "scored": len(ranked),
            "reviewed": reviewed_count,
            "outcomes": len(stages),
            "timedComparisons": len(time_advantages),
            "benchmarkCases": len(benchmark),
            "knownValuableBenchmarkCases": len(valuable_benchmarks),
            "matchedValuableBenchmarkCases": len(matched_valuable),
        },
        "interpretation": {
            "timeAdvantage": (
                "Negative hours means G-CCI detected the opportunity earlier "
                "than the traditional process."
            ),
            "recall": (
                "Discovery recall is reported only when the external benchmark "
                "corpus contains known valuable cases."
            ),
        },
    }
