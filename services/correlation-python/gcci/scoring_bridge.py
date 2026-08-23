from __future__ import annotations

from datetime import timedelta
from typing import Any

import httpx
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from .config import Settings, settings
from .database import HypothesisRevisionRow, ScoreJobRow, ScoreResultRow, utcnow
from .models import IncidentHypothesis, NormalizedEvent
from .utils import stable_hash


class CanonicalScoreResult(BaseModel):
    score: float = Field(ge=0, le=1)
    tier: str = Field(pattern="^[ABCD]$")
    reasons: list[str]
    confidence: dict[str, float]
    modelVersion: str
    reviewedAt: str


class CanonicalScoreResponse(BaseModel):
    result: CanonicalScoreResult
    policy: dict[str, bool]


class MaterialityDecision(BaseModel):
    material: bool
    reasons: list[str]
    current_input_hash: str
    previous_input_hash: str | None = None


def _truthy(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value != 0
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "y", "verified", "confirmed"}
    return False


def _float01(value: Any) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if number != number:
        return None
    return max(0.0, min(1.0, number))


def _all_attributes(events: list[NormalizedEvent]) -> list[dict[str, Any]]:
    attrs: list[dict[str, Any]] = []
    for event in events:
        merged: dict[str, Any] = {}
        merged.update(event.attributes or {})
        if isinstance(event.raw, dict):
            for key in (
                "suspected_at_fault",
                "improper_maintenance",
                "following_too_close",
                "improper_lane_change",
                "distracted_driving",
                "mechanical_failure",
                "carrier_usdot",
                "usdot",
                "carrier_name",
                "coverage_confirmed",
                "defendant_verified",
                "party_verified",
                "liability_score",
                "injury_score",
                "collectability_score",
                "defendant_resolution_score",
            ):
                if key in event.raw and key not in merged:
                    merged[key] = event.raw[key]
        attrs.append(merged)
    return attrs


def derive_mechanism(events: list[NormalizedEvent]) -> str:
    if any(e.wheel_off_hint for e in events):
        return "WheelOffIncident"
    if any("mechanical" in e.event_type.lower() for e in events):
        return "MechanicalFailureIncident"
    if any(e.debris_hint for e in events):
        return "DebrisIncident"
    if any(e.stalled_vehicle_hint for e in events):
        return "VehicleStall"

    text = " ".join(e.event_type.lower() for e in events)
    if "rear" in text:
        return "RearEndCollision"
    if "side" in text:
        return "SideswipeCollision"
    if "angle" in text or "intersection" in text:
        return "AngleCollision"
    return "UnknownIncident"


def derive_score_input(
    hypothesis: IncidentHypothesis,
    events: list[NormalizedEvent],
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Derive canonical scorer inputs from ontology-normalized evidence.

    This function deliberately keeps event correlation separate from liability and
    party attribution. Heuristics are conservative and versioned in the returned
    derivation metadata; they are not outcome-calibrated probabilities.
    """
    attrs = _all_attributes(events)

    explicit_liability = [
        score
        for a in attrs
        if (score := _float01(a.get("liability_score"))) is not None
    ]
    liability_signals = 0
    for a in attrs:
        liability_signals += sum(
            1
            for key in (
                "suspected_at_fault",
                "improper_maintenance",
                "following_too_close",
                "improper_lane_change",
                "distracted_driving",
                "mechanical_failure",
            )
            if _truthy(a.get(key))
        )
    liability = max(explicit_liability, default=0.0)
    if not explicit_liability:
        liability = min(0.8, 0.2 * liability_signals)

    explicit_injury = [
        score for a in attrs if (score := _float01(a.get("injury_score"))) is not None
    ]
    if explicit_injury:
        injury = max(explicit_injury)
    elif any(e.fatality_hint for e in events):
        injury = 1.0
    else:
        injury_count = sum(1 for e in events if e.injury_hint)
        injury = min(0.85, 0.55 + 0.10 * max(0, injury_count - 1)) if injury_count else 0.0

    explicit_collectability = [
        score
        for a in attrs
        if (score := _float01(a.get("collectability_score"))) is not None
    ]
    if explicit_collectability:
        collectability = max(explicit_collectability)
    else:
        commercial = any(e.commercial_vehicle_hint for e in events)
        carrier_known = any(
            bool(a.get("carrier_usdot") or a.get("usdot") or a.get("carrier_name")) for a in attrs
        )
        coverage_confirmed = any(_truthy(a.get("coverage_confirmed")) for a in attrs)
        collectability = min(
            1.0,
            (0.55 if commercial else 0.0)
            + (0.20 if carrier_known else 0.0)
            + (0.25 if coverage_confirmed else 0.0),
        )

    unique_sources = len({e.provenance.source_system for e in events})
    evidence_count = len(events)
    evidence = min(
        1.0,
        0.60 * min(1.0, unique_sources / 3.0)
        + 0.40 * min(1.0, evidence_count / 4.0),
    )

    explicit_defendant = [
        score
        for a in attrs
        if (score := _float01(a.get("defendant_resolution_score"))) is not None
    ]
    if explicit_defendant:
        defendant_resolution = max(explicit_defendant)
    else:
        defendant_verified = any(
            _truthy(a.get("defendant_verified")) or _truthy(a.get("party_verified")) for a in attrs
        )
        carrier_known = any(
            bool(a.get("carrier_usdot") or a.get("usdot") or a.get("carrier_name")) for a in attrs
        )
        defendant_resolution = 1.0 if defendant_verified else (0.5 if carrier_known else 0.0)

    high_contradictions = sum(
        1 for c in hypothesis.contradictions if str(c).strip().lower().startswith("high:")
    )
    other_contradictions = max(0, len(hypothesis.contradictions) - high_contradictions)

    # Correlation service does not resolve people. These remain zero unless a future
    # verified party-resolution adapter explicitly supplies them.
    num_parties = 0
    num_resolved_parties = 0

    score_input = {
        "scores": {
            "liability": round(liability, 4),
            "injury": round(injury, 4),
            "collectability": round(collectability, 4),
            "evidence": round(evidence, 4),
            "defendantResolution": round(defendant_resolution, 4),
        },
        "mechanism": derive_mechanism(events),
        "evidenceCount": evidence_count,
        "contradictions": {
            "highSeverityUnresolved": high_contradictions,
            "other": other_contradictions,
        },
        "numParties": num_parties,
        "numResolvedParties": num_resolved_parties,
    }

    derivation = {
        "version": "gcci-score-input-derivation-v1.0.0",
        "principles": {
            "correlationDoesNotImplyLiability": True,
            "correlationDoesNotImplyPartyAttribution": True,
            "contactEligibilityEvaluated": False,
        },
        "signals": {
            "explicitLiabilityScores": explicit_liability,
            "liabilitySignalCount": liability_signals,
            "fatalityHint": any(e.fatality_hint for e in events),
            "injuryEventCount": sum(1 for e in events if e.injury_hint),
            "commercialVehicleHint": any(e.commercial_vehicle_hint for e in events),
            "uniqueSourceCount": unique_sources,
            "evidenceCount": evidence_count,
        },
    }
    return score_input, derivation


def materiality_decision(
    *,
    current_revision: HypothesisRevisionRow,
    previous_revision: HypothesisRevisionRow | None,
    current_score_input: dict[str, Any],
    previous_score_input: dict[str, Any] | None,
    cfg: Settings = settings,
) -> MaterialityDecision:
    current_hash = stable_hash(current_score_input)
    previous_hash = stable_hash(previous_score_input) if previous_score_input is not None else None
    reasons: list[str] = []

    if previous_revision is None:
        reasons.append("first hypothesis revision")
    else:
        if current_revision.classification != previous_revision.classification:
            reasons.append("correlation classification changed")
        if abs(current_revision.machine_confidence - previous_revision.machine_confidence) >= cfg.score_material_confidence_delta:
            reasons.append(
                f"machine confidence changed by >= {cfg.score_material_confidence_delta:.2f}"
            )
        if set(current_revision.member_event_ids_json) != set(previous_revision.member_event_ids_json):
            reasons.append("supporting evidence membership changed")
        if current_revision.contradictions_json != previous_revision.contradictions_json:
            reasons.append("contradiction set changed")

    if previous_hash != current_hash:
        reasons.append("canonical score input changed")

    return MaterialityDecision(
        material=bool(reasons),
        reasons=reasons,
        current_input_hash=current_hash,
        previous_input_hash=previous_hash,
    )


async def enqueue_score_job(
    session: AsyncSession,
    *,
    hypothesis_id: str,
    revision: int,
    score_input: dict[str, Any],
    materiality: MaterialityDecision,
    derivation: dict[str, Any],
) -> ScoreJobRow | None:
    if not materiality.material:
        return None

    values = {
        "hypothesis_id": hypothesis_id,
        "revision": revision,
        "score_input_json": {
            "canonicalInput": score_input,
            "derivation": derivation,
        },
        "materiality_json": materiality.model_dump(mode="json"),
        "status": "PENDING",
        "attempts": 0,
        "next_attempt_at": utcnow(),
        "updated_at": utcnow(),
    }
    stmt = (
        insert(ScoreJobRow)
        .values(**values)
        .on_conflict_do_nothing(index_elements=[ScoreJobRow.hypothesis_id, ScoreJobRow.revision])
        .returning(ScoreJobRow)
    )
    return (await session.execute(stmt)).scalar_one_or_none()


class CanonicalScorerClient:
    def __init__(self, cfg: Settings = settings):
        self.cfg = cfg

    async def score(self, score_input: dict[str, Any]) -> CanonicalScoreResponse:
        timeout = httpx.Timeout(self.cfg.canonical_scorer_timeout_seconds)
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(self.cfg.canonical_scorer_url, json=score_input)
            response.raise_for_status()
            parsed = CanonicalScoreResponse.model_validate(response.json())
            if parsed.policy.get("contactEligibilityEvaluated") is not False:
                raise ValueError("Canonical scorer violated policy boundary: contact eligibility evaluated")
            return parsed


async def previous_revision_and_score_input(
    session: AsyncSession,
    hypothesis_id: str,
    revision: int,
) -> tuple[HypothesisRevisionRow | None, dict[str, Any] | None]:
    if revision <= 1:
        return None, None

    previous_revision = (
        await session.execute(
            select(HypothesisRevisionRow).where(
                HypothesisRevisionRow.hypothesis_id == hypothesis_id,
                HypothesisRevisionRow.revision == revision - 1,
            )
        )
    ).scalar_one_or_none()
    previous_job = (
        await session.execute(
            select(ScoreJobRow).where(
                ScoreJobRow.hypothesis_id == hypothesis_id,
                ScoreJobRow.revision < revision,
            ).order_by(ScoreJobRow.revision.desc()).limit(1)
        )
    ).scalar_one_or_none()
    previous_input = None
    if previous_job:
        previous_input = previous_job.score_input_json.get("canonicalInput")
    return previous_revision, previous_input


async def persist_score_result(
    session: AsyncSession,
    *,
    job: ScoreJobRow,
    response: CanonicalScoreResponse,
) -> ScoreResultRow:
    result = response.result
    stmt = (
        insert(ScoreResultRow)
        .values(
            hypothesis_id=job.hypothesis_id,
            revision=job.revision,
            score=result.score,
            tier=result.tier,
            model_version=result.modelVersion,
            result_json=response.model_dump(mode="json"),
            scored_at=utcnow(),
        )
        .on_conflict_do_update(
            index_elements=[ScoreResultRow.hypothesis_id, ScoreResultRow.revision],
            set_={
                "score": result.score,
                "tier": result.tier,
                "model_version": result.modelVersion,
                "result_json": response.model_dump(mode="json"),
                "scored_at": utcnow(),
            },
        )
        .returning(ScoreResultRow)
    )
    return (await session.execute(stmt)).scalar_one()


def retry_delay_seconds(attempts: int, cfg: Settings = settings) -> int:
    raw = cfg.scoring_retry_base_seconds * (2 ** max(0, attempts - 1))
    return min(cfg.scoring_retry_max_seconds, raw)


def next_retry_time(attempts: int, cfg: Settings = settings):
    return utcnow() + timedelta(seconds=retry_delay_seconds(attempts, cfg))
