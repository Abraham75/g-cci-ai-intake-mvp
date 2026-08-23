from __future__ import annotations

from typing import Iterable

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from .database import EvidenceAcquisitionTaskRow, ScoreResultRow, utcnow
from .evidence_gaps import rank_evidence_gaps
from .models import EvidenceGap, IncidentHypothesis, NormalizedEvent


ACQUISITION_PRIORITY_MODEL_VERSION = "gcci-evidence-acquisition-priority-v1.0.0"
TIER_MULTIPLIER: dict[str, float] = {
    "A": 1.00,
    "B": 0.90,
    "C": 0.75,
    "D": 0.55,
}


def compute_acquisition_priority(
    *, expected_information_gain: float,
    case_opportunity_score: float,
    tier: str,
) -> float:
    """Rank evidence work without conflating case value and evidentiary value.

    EIG remains the dominant signal. COS only modulates queue urgency, so a
    preservation-critical gap is never zeroed merely because the case score is low.
    Contact eligibility is intentionally absent from this function.
    """
    eig = max(0.0, min(1.0, float(expected_information_gain)))
    cos = max(0.0, min(1.0, float(case_opportunity_score)))
    tier_multiplier = TIER_MULTIPLIER.get(tier, TIER_MULTIPLIER["D"])
    priority = eig * (0.55 + 0.45 * cos) * tier_multiplier
    return round(max(0.0, min(1.0, priority)), 4)


def _hypothesis_from_payload(payload: dict) -> IncidentHypothesis:
    return IncidentHypothesis.model_validate(payload)


async def build_acquisition_tasks_for_score(
    session: AsyncSession,
    *,
    score_result: ScoreResultRow,
    hypothesis_payload: dict,
    events: list[NormalizedEvent],
) -> list[EvidenceAcquisitionTaskRow]:
    hypothesis = _hypothesis_from_payload(hypothesis_payload)
    # Persistent camera inventory is not yet part of the PostGIS schema, so this
    # queue intentionally ranks gaps with no assumed camera availability. When a
    # camera inventory adapter is persisted, pass nearest-camera candidates here.
    gaps = rank_evidence_gaps(hypothesis, events, nearest_cameras=[])

    tasks: list[EvidenceAcquisitionTaskRow] = []
    for gap in gaps:
        priority = compute_acquisition_priority(
            expected_information_gain=gap.expected_information_gain,
            case_opportunity_score=score_result.score,
            tier=score_result.tier,
        )
        values = {
            "hypothesis_id": score_result.hypothesis_id,
            "revision": score_result.revision,
            "score_result_id": score_result.id,
            "evidence_type": gap.evidence_type,
            "question": gap.question,
            "recommended_action": gap.recommended_action,
            "expected_information_gain": gap.expected_information_gain,
            "acquisition_priority_score": priority,
            "case_opportunity_score": score_result.score,
            "tier": score_result.tier,
            "status": "OPEN",
            "priority_model_version": ACQUISITION_PRIORITY_MODEL_VERSION,
            "gap_json": gap.model_dump(mode="json"),
            "updated_at": utcnow(),
        }
        stmt = (
            insert(EvidenceAcquisitionTaskRow)
            .values(**values)
            .on_conflict_do_update(
                index_elements=[
                    EvidenceAcquisitionTaskRow.hypothesis_id,
                    EvidenceAcquisitionTaskRow.revision,
                    EvidenceAcquisitionTaskRow.evidence_type,
                ],
                set_={
                    "score_result_id": score_result.id,
                    "question": gap.question,
                    "recommended_action": gap.recommended_action,
                    "expected_information_gain": gap.expected_information_gain,
                    "acquisition_priority_score": priority,
                    "case_opportunity_score": score_result.score,
                    "tier": score_result.tier,
                    "priority_model_version": ACQUISITION_PRIORITY_MODEL_VERSION,
                    "gap_json": gap.model_dump(mode="json"),
                    "updated_at": utcnow(),
                },
            )
            .returning(EvidenceAcquisitionTaskRow)
        )
        tasks.append((await session.execute(stmt)).scalar_one())

    return sorted(tasks, key=lambda t: t.acquisition_priority_score, reverse=True)


async def acquisition_tasks_for_hypothesis(
    session: AsyncSession,
    hypothesis_id: str,
    *,
    only_open: bool = False,
) -> list[EvidenceAcquisitionTaskRow]:
    query = select(EvidenceAcquisitionTaskRow).where(
        EvidenceAcquisitionTaskRow.hypothesis_id == hypothesis_id
    )
    if only_open:
        query = query.where(EvidenceAcquisitionTaskRow.status == "OPEN")
    rows = (
        await session.execute(
            query.order_by(
                EvidenceAcquisitionTaskRow.revision.desc(),
                EvidenceAcquisitionTaskRow.acquisition_priority_score.desc(),
            )
        )
    ).scalars().all()
    return list(rows)


async def acquisition_queue(
    session: AsyncSession,
    *,
    limit: int = 100,
) -> list[EvidenceAcquisitionTaskRow]:
    rows = (
        await session.execute(
            select(EvidenceAcquisitionTaskRow)
            .where(EvidenceAcquisitionTaskRow.status == "OPEN")
            .order_by(EvidenceAcquisitionTaskRow.acquisition_priority_score.desc())
            .limit(limit)
        )
    ).scalars().all()
    return list(rows)
