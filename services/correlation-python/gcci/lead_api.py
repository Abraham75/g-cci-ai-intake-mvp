from __future__ import annotations

import json
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select, text

from .database import DecisionLedgerRow, ScoreResultRow, SessionLocal
from .lead_qualification import (
    STAGE_SCORE,
    build_lead_qualification_for_score,
    latest_lead_qualification,
    resolution_tasks_for_hypothesis,
)
from .ledger import append_ledger_entry
from .security import Actor, require_roles


router = APIRouter(
    tags=["lead-qualification-resolution"],
    dependencies=[Depends(require_roles("INVESTIGATOR", "ATTORNEY", "COMPLIANCE", "AUDITOR"))],
)


class ProspectEvidenceInput(BaseModel):
    party_role: str = "INJURED_PARTY"
    target_stage: str = Field(pattern="^(CANDIDATE|CORROBORATED|VERIFIED)$")
    display_label: str | None = Field(default=None, max_length=255)
    source_type: str = Field(min_length=1, max_length=64)
    source_reference: str = Field(min_length=1, max_length=255)
    confidence: float = Field(ge=0, le=1)
    lawful_access_basis: str = Field(min_length=1, max_length=64)
    evidence_entry_ids: list[str] = Field(min_length=1, max_length=50)
    note: str | None = Field(default=None, max_length=2000)


_STAGE_ORDER = ["UNKNOWN", "CANDIDATE", "CORROBORATED", "VERIFIED"]


async def _latest_score(session, hypothesis_id: str) -> ScoreResultRow | None:
    return (
        await session.execute(
            select(ScoreResultRow)
            .where(ScoreResultRow.hypothesis_id == hypothesis_id)
            .order_by(ScoreResultRow.revision.desc())
            .limit(1)
        )
    ).scalar_one_or_none()


@router.get("/hypotheses/{hypothesis_id}/qualification")
async def get_qualification(hypothesis_id: str) -> dict:
    async with SessionLocal() as session:
        qualification = await latest_lead_qualification(session, hypothesis_id)
        if qualification is None:
            score = await _latest_score(session, hypothesis_id)
            if score is None:
                raise HTTPException(404, "No completed canonical score exists for this hypothesis")
            return {
                "hypothesisId": hypothesis_id,
                "status": "PENDING_QUALIFICATION",
                "latestScoredRevision": score.revision,
                "policy": {
                    "contactEligibilityEvaluated": False,
                    "requiresIndependentComplianceGate": True,
                },
            }
        qualification["policy"] = {
            "identityInferredFromWeakCorrelation": False,
            "contactEligibilityEvaluated": False,
            "requiresIndependentComplianceGate": True,
        }
        return qualification


@router.post("/hypotheses/{hypothesis_id}/qualification/refresh")
async def refresh_qualification(hypothesis_id: str) -> dict:
    async with SessionLocal() as session:
        async with session.begin():
            score = await _latest_score(session, hypothesis_id)
            if score is None:
                raise HTTPException(404, "No completed canonical score exists for this hypothesis")
            return await build_lead_qualification_for_score(session, score_result=score)


@router.get("/hypotheses/{hypothesis_id}/resolution-tasks")
async def get_resolution_tasks(
    hypothesis_id: str,
    open_only: bool = Query(default=True),
) -> list[dict]:
    async with SessionLocal() as session:
        return await resolution_tasks_for_hypothesis(session, hypothesis_id, open_only=open_only)


@router.get("/hypotheses/{hypothesis_id}/prospects")
async def get_prospects(hypothesis_id: str) -> list[dict]:
    async with SessionLocal() as session:
        rows = (
            await session.execute(
                text(
                    """
                    SELECT id, party_role, stage, display_label, source_type, source_reference,
                           confidence, verified, lawful_access_basis, notes_json, created_at, updated_at
                    FROM prospect_resolution_records
                    WHERE hypothesis_id = :hypothesis_id
                    ORDER BY verified DESC, confidence DESC, updated_at DESC
                    """
                ),
                {"hypothesis_id": hypothesis_id},
            )
        ).mappings().all()
        return [
            {
                "id": row["id"],
                "partyRole": row["party_role"],
                "stage": row["stage"],
                "displayLabel": row["display_label"],
                "sourceType": row["source_type"],
                "sourceReference": row["source_reference"],
                "confidence": float(row["confidence"]),
                "verified": bool(row["verified"]),
                "lawfulAccessBasis": row["lawful_access_basis"],
                "notes": row["notes_json"],
                "createdAt": row["created_at"].isoformat(),
                "updatedAt": row["updated_at"].isoformat(),
            }
            for row in rows
        ]


@router.post("/hypotheses/{hypothesis_id}/prospects/evidence")
async def record_prospect_evidence(
    hypothesis_id: str,
    body: ProspectEvidenceInput,
    actor: Actor = Depends(require_roles("INVESTIGATOR", "ATTORNEY", "COMPLIANCE")),
) -> dict:
    """Advance claimant resolution using referenced evidence and authenticated review identity."""
    target_index = _STAGE_ORDER.index(body.target_stage)
    async with SessionLocal() as session:
        async with session.begin():
            existing = (
                await session.execute(
                    text(
                        """
                        SELECT id, stage, confidence, verified
                        FROM prospect_resolution_records
                        WHERE hypothesis_id = :hypothesis_id AND party_role = :party_role
                        ORDER BY updated_at DESC
                        LIMIT 1
                        FOR UPDATE
                        """
                    ),
                    {"hypothesis_id": hypothesis_id, "party_role": body.party_role},
                )
            ).mappings().first()

            current_stage = str(existing["stage"]) if existing else "UNKNOWN"
            current_index = _STAGE_ORDER.index(current_stage)
            if target_index < current_index:
                raise HTTPException(409, "Prospect resolution stage cannot move backward")
            if target_index > current_index + 1:
                raise HTTPException(400, "Prospect resolution stages cannot be skipped")
            if body.target_stage == "VERIFIED":
                if body.confidence < 0.90:
                    raise HTTPException(400, "VERIFIED requires confidence >= 0.90")
                if body.lawful_access_basis == "NotEstablished":
                    raise HTTPException(400, "VERIFIED requires an established lawful access basis")

            unique_evidence_ids = list(dict.fromkeys(body.evidence_entry_ids))
            existing_evidence_ids = (
                await session.execute(
                    select(DecisionLedgerRow.id).where(DecisionLedgerRow.id.in_(unique_evidence_ids))
                )
            ).scalars().all()
            if len(existing_evidence_ids) != len(unique_evidence_ids):
                raise HTTPException(400, "Every evidence_entry_id must reference an existing ledger entry")

            record_id = str(existing["id"]) if existing else str(uuid4())
            notes = [
                {
                    "reviewedBy": actor.name,
                    "note": body.note,
                    "evidenceEntryIds": unique_evidence_ids,
                    "stage": body.target_stage,
                }
            ]
            await session.execute(
                text(
                    """
                    INSERT INTO prospect_resolution_records (
                        id, hypothesis_id, party_role, stage, display_label, source_type,
                        source_reference, confidence, verified, lawful_access_basis,
                        notes_json, created_at, updated_at
                    ) VALUES (
                        :id, :hypothesis_id, :party_role, :stage, :display_label, :source_type,
                        :source_reference, :confidence, :verified, :lawful_access_basis,
                        CAST(:notes AS jsonb), now(), now()
                    )
                    ON CONFLICT (id) DO UPDATE SET
                        stage = EXCLUDED.stage,
                        display_label = COALESCE(EXCLUDED.display_label, prospect_resolution_records.display_label),
                        source_type = EXCLUDED.source_type,
                        source_reference = EXCLUDED.source_reference,
                        confidence = GREATEST(prospect_resolution_records.confidence, EXCLUDED.confidence),
                        verified = EXCLUDED.verified,
                        lawful_access_basis = EXCLUDED.lawful_access_basis,
                        notes_json = prospect_resolution_records.notes_json || EXCLUDED.notes_json,
                        updated_at = now()
                    """
                ),
                {
                    "id": record_id,
                    "hypothesis_id": hypothesis_id,
                    "party_role": body.party_role,
                    "stage": body.target_stage,
                    "display_label": body.display_label,
                    "source_type": body.source_type,
                    "source_reference": body.source_reference,
                    "confidence": body.confidence,
                    "verified": body.target_stage == "VERIFIED",
                    "lawful_access_basis": body.lawful_access_basis,
                    "notes": json.dumps(notes),
                },
            )

            evidence_entry = await append_ledger_entry(
                session,
                entry_type="ProspectResolutionEvidence",
                subject_id=hypothesis_id,
                payload={
                    "action": "prospect-resolution-stage-recorded",
                    "prospectId": record_id,
                    "partyRole": body.party_role,
                    "previousStage": current_stage,
                    "newStage": body.target_stage,
                    "sourceType": body.source_type,
                    "sourceReference": body.source_reference,
                    "confidence": body.confidence,
                    "lawfulAccessBasis": body.lawful_access_basis,
                    "reviewedBy": actor.name,
                    "policy": {
                        "contactValueStored": False,
                        "contactEligibilityEvaluated": False,
                    },
                },
                produced_by=f"human:{actor.name}",
                source_system="POST:/hypotheses/:id/prospects/evidence",
                input_entry_ids=unique_evidence_ids,
            )

            score = await _latest_score(session, hypothesis_id)
            qualification = None
            if score is not None:
                qualification = await build_lead_qualification_for_score(
                    session,
                    score_result=score,
                    score_ledger_entry_id=evidence_entry.id,
                )

            return {
                "prospect": {
                    "id": record_id,
                    "partyRole": body.party_role,
                    "stage": body.target_stage,
                    "resolutionScore": STAGE_SCORE[body.target_stage],
                    "displayLabel": body.display_label,
                    "sourceType": body.source_type,
                    "sourceReference": body.source_reference,
                    "confidence": body.confidence,
                    "verified": body.target_stage == "VERIFIED",
                    "lawfulAccessBasis": body.lawful_access_basis,
                },
                "qualification": qualification,
                "policy": {
                    "contactValueStored": False,
                    "contactEligibilityEvaluated": False,
                    "requiresIndependentComplianceGate": True,
                },
            }
