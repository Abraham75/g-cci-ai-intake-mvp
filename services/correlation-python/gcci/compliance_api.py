from __future__ import annotations

import json
from typing import Literal
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from .contact_vault import decrypt_contact_value, encrypt_contact_value
from .database import SessionLocal
from .ledger import append_ledger_entry
from .security import Actor, require_roles

router = APIRouter(tags=["compliance-contact-vault"])

LegalAccessBasis = Literal[
    "NotEstablished",
    "PublicRecord",
    "OpenRecordsRequest",
    "ClientProvided",
    "OtherLawfulBasis",
]
SolicitationReviewStatus = Literal[
    "NotReviewed",
    "WithinHoldPeriod",
    "ClearedByCounsel",
    "RejectedByCounsel",
]
ContactStatus = Literal["ACTIVE", "SUPPRESSED", "REVOKED"]


class ComplianceReviewInput(BaseModel):
    legal_access_basis: LegalAccessBasis
    solicitation_review_status: SolicitationReviewStatus
    suppression_checked: bool
    solicitation_hold_days: int | None = Field(default=None, ge=0, le=3650)
    note: str | None = Field(default=None, max_length=2000)


class ContactPointInput(BaseModel):
    prospect_id: str = Field(min_length=1, max_length=64)
    contact_type: Literal["PHONE", "EMAIL", "ADDRESS", "OTHER"]
    value: str = Field(min_length=1, max_length=2000)
    source_type: str = Field(min_length=1, max_length=64)
    source_reference: str = Field(min_length=1, max_length=255)
    lawful_access_basis: LegalAccessBasis
    verification_confidence: float = Field(ge=0, le=1)
    verified: bool = False


class RevealInput(BaseModel):
    reason: str = Field(min_length=8, max_length=1000)


class ContactStatusInput(BaseModel):
    status: ContactStatus
    reason: str = Field(min_length=8, max_length=1000)


def _eligibility(legal_access_basis: str, review_status: str, suppression_checked: bool) -> str:
    if legal_access_basis == "NotEstablished":
        return "Ineligible"
    if review_status != "ClearedByCounsel":
        return "Ineligible"
    if not suppression_checked:
        return "Ineligible"
    return "Eligible"


async def _gate(session, hypothesis_id: str) -> dict:
    row = (
        await session.execute(
            text(
                """
                SELECT hypothesis_id, legal_access_basis, solicitation_review_status,
                       solicitation_hold_days, suppression_checked,
                       contact_eligibility_status, notes_json, reviewed_by,
                       reviewed_at, updated_at
                FROM compliance_gate_states
                WHERE hypothesis_id = :hypothesis_id
                """
            ),
            {"hypothesis_id": hypothesis_id},
        )
    ).mappings().first()
    if row is None:
        return {
            "subjectId": hypothesis_id,
            "legalAccessBasis": "NotEstablished",
            "solicitationReviewStatus": "NotReviewed",
            "solicitationHoldDays": None,
            "suppressionChecked": False,
            "contactEligibilityStatus": "NotEvaluated",
            "notes": [],
            "reviewedBy": None,
            "reviewedAt": None,
            "lastUpdated": None,
        }
    return {
        "subjectId": row["hypothesis_id"],
        "legalAccessBasis": row["legal_access_basis"],
        "solicitationReviewStatus": row["solicitation_review_status"],
        "solicitationHoldDays": row["solicitation_hold_days"],
        "suppressionChecked": bool(row["suppression_checked"]),
        "contactEligibilityStatus": row["contact_eligibility_status"],
        "notes": row["notes_json"] or [],
        "reviewedBy": row["reviewed_by"],
        "reviewedAt": row["reviewed_at"].isoformat() if row["reviewed_at"] else None,
        "lastUpdated": row["updated_at"].isoformat() if row["updated_at"] else None,
    }


async def _latest_qualification(session, hypothesis_id: str) -> dict | None:
    row = (
        await session.execute(
            text(
                """
                SELECT l.revision, l.stage, l.case_qualified, l.qualification_score,
                       h.current_revision
                FROM lead_qualification_snapshots l
                JOIN incident_hypotheses h ON h.id = l.hypothesis_id
                WHERE l.hypothesis_id = :hypothesis_id
                ORDER BY l.revision DESC
                LIMIT 1
                """
            ),
            {"hypothesis_id": hypothesis_id},
        )
    ).mappings().first()
    if row is None:
        return None
    revision = int(row["revision"])
    current_revision = int(row["current_revision"])
    return {
        "revision": revision,
        "currentHypothesisRevision": current_revision,
        "isCurrent": revision == current_revision,
        "stage": row["stage"],
        "caseQualified": bool(row["case_qualified"]),
        "qualificationScore": float(row["qualification_score"]),
    }


def _outreach_ready(qualification: dict | None, gate: dict, prospect: object, contact: object) -> bool:
    return bool(
        qualification
        and qualification["isCurrent"]
        and qualification["caseQualified"]
        and qualification["stage"] == "S3_RESOLVED_PROSPECT"
        and gate["contactEligibilityStatus"] == "Eligible"
        and prospect
        and contact
    )


@router.get("/hypotheses/{hypothesis_id}/compliance")
async def get_compliance_gate(
    hypothesis_id: str,
    _: Actor = Depends(require_roles("INVESTIGATOR", "ATTORNEY", "COMPLIANCE", "AUDITOR")),
) -> dict:
    async with SessionLocal() as session:
        return await _gate(session, hypothesis_id)


@router.post("/hypotheses/{hypothesis_id}/compliance/review")
async def review_compliance_gate(
    hypothesis_id: str,
    body: ComplianceReviewInput,
    actor: Actor = Depends(require_roles("COMPLIANCE")),
) -> dict:
    eligibility = _eligibility(
        body.legal_access_basis,
        body.solicitation_review_status,
        body.suppression_checked,
    )
    async with SessionLocal() as session:
        async with session.begin():
            exists = (
                await session.execute(
                    text("SELECT 1 FROM incident_hypotheses WHERE id = :id"),
                    {"id": hypothesis_id},
                )
            ).first()
            if not exists:
                raise HTTPException(404, "Unknown hypothesis")

            current = await _gate(session, hypothesis_id)
            notes = list(current.get("notes") or [])
            if body.note:
                notes.append(f"[{actor.name}] {body.note}")

            await session.execute(
                text(
                    """
                    INSERT INTO compliance_gate_states (
                        hypothesis_id, legal_access_basis, solicitation_review_status,
                        solicitation_hold_days, suppression_checked,
                        contact_eligibility_status, notes_json, reviewed_by,
                        reviewed_at, created_at, updated_at
                    ) VALUES (
                        :hypothesis_id, :legal_access_basis, :review_status,
                        :hold_days, :suppression_checked, :eligibility,
                        CAST(:notes AS jsonb), :reviewed_by, now(), now(), now()
                    )
                    ON CONFLICT (hypothesis_id) DO UPDATE SET
                        legal_access_basis = EXCLUDED.legal_access_basis,
                        solicitation_review_status = EXCLUDED.solicitation_review_status,
                        solicitation_hold_days = EXCLUDED.solicitation_hold_days,
                        suppression_checked = EXCLUDED.suppression_checked,
                        contact_eligibility_status = EXCLUDED.contact_eligibility_status,
                        notes_json = EXCLUDED.notes_json,
                        reviewed_by = EXCLUDED.reviewed_by,
                        reviewed_at = now(),
                        updated_at = now()
                    """
                ),
                {
                    "hypothesis_id": hypothesis_id,
                    "legal_access_basis": body.legal_access_basis,
                    "review_status": body.solicitation_review_status,
                    "hold_days": body.solicitation_hold_days,
                    "suppression_checked": body.suppression_checked,
                    "eligibility": eligibility,
                    "notes": json.dumps(notes),
                    "reviewed_by": actor.name,
                },
            )
            await append_ledger_entry(
                session,
                entry_type="ComplianceDecision",
                subject_id=hypothesis_id,
                payload={
                    "action": "durable-compliance-review",
                    "reviewer": actor.name,
                    "legalAccessBasis": body.legal_access_basis,
                    "solicitationReviewStatus": body.solicitation_review_status,
                    "suppressionChecked": body.suppression_checked,
                    "solicitationHoldDays": body.solicitation_hold_days,
                    "resultingEligibility": eligibility,
                },
                produced_by=f"human:{actor.name}",
                source_system="PostgreSQL/PostGIS compliance gate",
            )
        return await _gate(session, hypothesis_id)


@router.get("/hypotheses/{hypothesis_id}/contacts")
async def list_contacts(
    hypothesis_id: str,
    _: Actor = Depends(require_roles("INVESTIGATOR", "ATTORNEY", "COMPLIANCE", "AUDITOR")),
) -> list[dict]:
    async with SessionLocal() as session:
        rows = (
            await session.execute(
                text(
                    """
                    SELECT cp.id, cp.prospect_id, cp.contact_type, cp.masked_value,
                           cp.source_type, cp.source_reference, cp.lawful_access_basis,
                           cp.verification_confidence, cp.verified, cp.status,
                           cp.created_by, cp.created_at, cp.updated_at,
                           pr.party_role, pr.stage AS prospect_stage
                    FROM contact_points cp
                    JOIN prospect_resolution_records pr ON pr.id = cp.prospect_id
                    WHERE cp.hypothesis_id = :hypothesis_id
                    ORDER BY cp.verified DESC, cp.verification_confidence DESC, cp.created_at DESC
                    """
                ),
                {"hypothesis_id": hypothesis_id},
            )
        ).mappings().all()
        return [
            {
                "id": row["id"],
                "prospectId": row["prospect_id"],
                "partyRole": row["party_role"],
                "prospectStage": row["prospect_stage"],
                "contactType": row["contact_type"],
                "maskedValue": row["masked_value"],
                "sourceType": row["source_type"],
                "sourceReference": row["source_reference"],
                "lawfulAccessBasis": row["lawful_access_basis"],
                "verificationConfidence": float(row["verification_confidence"]),
                "verified": bool(row["verified"]),
                "status": row["status"],
                "createdBy": row["created_by"],
                "createdAt": row["created_at"].isoformat(),
                "updatedAt": row["updated_at"].isoformat(),
            }
            for row in rows
        ]


@router.post("/hypotheses/{hypothesis_id}/contacts")
async def add_contact(
    hypothesis_id: str,
    body: ContactPointInput,
    actor: Actor = Depends(require_roles("INVESTIGATOR", "COMPLIANCE")),
) -> dict:
    if body.verified and body.verification_confidence < 0.90:
        raise HTTPException(400, "A VERIFIED contact requires verification_confidence >= 0.90")
    if body.lawful_access_basis == "NotEstablished":
        raise HTTPException(409, "Contact storage requires an established lawful-access basis")

    aad = f"gcci:{hypothesis_id}:{body.prospect_id}:{body.contact_type}"
    try:
        encrypted, nonce, fingerprint, masked = encrypt_contact_value(
            body.contact_type, body.value, aad=aad
        )
    except RuntimeError as exc:
        raise HTTPException(503, str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc

    contact_id = str(uuid4())
    try:
        async with SessionLocal() as session:
            async with session.begin():
                prospect = (
                    await session.execute(
                        text(
                            """
                            SELECT id, party_role, stage, lawful_access_basis
                            FROM prospect_resolution_records
                            WHERE id = :prospect_id AND hypothesis_id = :hypothesis_id
                            """
                        ),
                        {"prospect_id": body.prospect_id, "hypothesis_id": hypothesis_id},
                    )
                ).mappings().first()
                if prospect is None:
                    raise HTTPException(404, "Unknown prospect for hypothesis")
                if prospect["party_role"] != "INJURED_PARTY" or prospect["stage"] != "VERIFIED":
                    raise HTTPException(409, "Contact storage requires a VERIFIED injured-party prospect")
                if prospect["lawful_access_basis"] == "NotEstablished":
                    raise HTTPException(409, "Verified prospect is missing a lawful-access basis")

                await session.execute(
                    text(
                        """
                        INSERT INTO contact_points (
                            id, hypothesis_id, prospect_id, contact_type,
                            encrypted_value, nonce, value_fingerprint, masked_value,
                            source_type, source_reference, lawful_access_basis,
                            verification_confidence, verified, status, created_by,
                            created_at, updated_at
                        ) VALUES (
                            :id, :hypothesis_id, :prospect_id, :contact_type,
                            :encrypted_value, :nonce, :fingerprint, :masked_value,
                            :source_type, :source_reference, :lawful_access_basis,
                            :confidence, :verified, 'ACTIVE', :created_by, now(), now()
                        )
                        """
                    ),
                    {
                        "id": contact_id,
                        "hypothesis_id": hypothesis_id,
                        "prospect_id": body.prospect_id,
                        "contact_type": body.contact_type,
                        "encrypted_value": encrypted,
                        "nonce": nonce,
                        "fingerprint": fingerprint,
                        "masked_value": masked,
                        "source_type": body.source_type,
                        "source_reference": body.source_reference,
                        "lawful_access_basis": body.lawful_access_basis,
                        "confidence": body.verification_confidence,
                        "verified": body.verified,
                        "created_by": actor.name,
                    },
                )
                await append_ledger_entry(
                    session,
                    entry_type="ContactResolution",
                    subject_id=hypothesis_id,
                    payload={
                        "action": "encrypted-contact-added",
                        "contactPointId": contact_id,
                        "prospectId": body.prospect_id,
                        "partyRole": "INJURED_PARTY",
                        "contactType": body.contact_type,
                        "maskedValue": masked,
                        "sourceType": body.source_type,
                        "sourceReference": body.source_reference,
                        "lawfulAccessBasis": body.lawful_access_basis,
                        "verificationConfidence": body.verification_confidence,
                        "verified": body.verified,
                    },
                    produced_by=f"human:{actor.name}",
                    source_system="encrypted-contact-vault",
                )
    except IntegrityError as exc:
        if "uq_contact_fingerprint_hypothesis" in str(exc):
            raise HTTPException(409, "Duplicate contact value for hypothesis") from exc
        raise

    return {"id": contact_id, "maskedValue": masked, "status": "ACTIVE"}


@router.post("/contacts/{contact_id}/status")
async def set_contact_status(
    contact_id: str,
    body: ContactStatusInput,
    actor: Actor = Depends(require_roles("COMPLIANCE")),
) -> dict:
    async with SessionLocal() as session:
        async with session.begin():
            row = (
                await session.execute(
                    text(
                        """
                        UPDATE contact_points
                        SET status = :status, updated_at = now()
                        WHERE id = :id
                        RETURNING hypothesis_id, masked_value, status
                        """
                    ),
                    {"id": contact_id, "status": body.status},
                )
            ).mappings().first()
            if row is None:
                raise HTTPException(404, "Unknown contact point")
            await append_ledger_entry(
                session,
                entry_type="ContactResolution",
                subject_id=row["hypothesis_id"],
                payload={
                    "action": "contact-status-changed",
                    "contactPointId": contact_id,
                    "maskedValue": row["masked_value"],
                    "newStatus": body.status,
                    "reason": body.reason,
                },
                produced_by=f"human:{actor.name}",
                source_system="encrypted-contact-vault",
            )
    return {"id": contact_id, "status": body.status}


@router.post("/contacts/{contact_id}/reveal")
async def reveal_contact(
    contact_id: str,
    body: RevealInput,
    actor: Actor = Depends(require_roles("ATTORNEY", "COMPLIANCE")),
) -> dict:
    allowed = False
    audit_id = str(uuid4())
    row = None

    async with SessionLocal() as session:
        async with session.begin():
            row = (
                await session.execute(
                    text(
                        """
                        SELECT cp.id, cp.hypothesis_id, cp.prospect_id, cp.contact_type,
                               cp.encrypted_value, cp.nonce, cp.masked_value,
                               cp.status, cp.verified, pr.party_role,
                               pr.stage AS prospect_stage
                        FROM contact_points cp
                        JOIN prospect_resolution_records pr ON pr.id = cp.prospect_id
                        WHERE cp.id = :id
                        """
                    ),
                    {"id": contact_id},
                )
            ).mappings().first()
            if row is None:
                raise HTTPException(404, "Unknown contact point")

            gate = await _gate(session, row["hypothesis_id"])
            qualification = await _latest_qualification(session, row["hypothesis_id"])
            allowed = bool(
                row["status"] == "ACTIVE"
                and row["verified"]
                and row["party_role"] == "INJURED_PARTY"
                and row["prospect_stage"] == "VERIFIED"
                and qualification
                and qualification["isCurrent"]
                and qualification["caseQualified"]
                and qualification["stage"] == "S3_RESOLVED_PROSPECT"
                and gate["contactEligibilityStatus"] == "Eligible"
            )
            await session.execute(
                text(
                    """
                    INSERT INTO contact_access_audit (
                        id, contact_point_id, hypothesis_id, actor, action,
                        reason, allowed, gate_snapshot_json, created_at
                    ) VALUES (
                        :id, :contact_id, :hypothesis_id, :actor, 'REVEAL',
                        :reason, :allowed, CAST(:gate AS jsonb), now()
                    )
                    """
                ),
                {
                    "id": audit_id,
                    "contact_id": contact_id,
                    "hypothesis_id": row["hypothesis_id"],
                    "actor": actor.name,
                    "reason": body.reason,
                    "allowed": allowed,
                    "gate": json.dumps({"gate": gate, "qualification": qualification}),
                },
            )
            await append_ledger_entry(
                session,
                entry_type="ContactAccess",
                subject_id=row["hypothesis_id"],
                payload={
                    "action": "contact-reveal-attempt",
                    "contactPointId": contact_id,
                    "actor": actor.name,
                    "allowed": allowed,
                    "reason": body.reason,
                    "gateStatus": gate["contactEligibilityStatus"],
                    "qualificationRevision": qualification["revision"] if qualification else None,
                    "qualificationCurrent": qualification["isCurrent"] if qualification else False,
                },
                produced_by=f"human:{actor.name}",
                source_system="encrypted-contact-vault",
            )

    if not allowed or row is None:
        raise HTTPException(403, "Contact reveal blocked by qualification/verification/compliance gates")

    aad = f"gcci:{row['hypothesis_id']}:{row['prospect_id']}:{row['contact_type']}"
    try:
        value = decrypt_contact_value(row["encrypted_value"], row["nonce"], aad=aad)
    except RuntimeError as exc:
        raise HTTPException(503, str(exc)) from exc

    return {
        "id": contact_id,
        "contactType": row["contact_type"],
        "value": value,
        "maskedValue": row["masked_value"],
        "auditId": audit_id,
    }


@router.post("/hypotheses/{hypothesis_id}/activate")
async def activate_for_outreach(
    hypothesis_id: str,
    actor: Actor = Depends(require_roles("ATTORNEY", "COMPLIANCE")),
) -> dict:
    allowed = False
    reasons: list[str] = []
    attempt_id = str(uuid4())

    async with SessionLocal() as session:
        async with session.begin():
            gate = await _gate(session, hypothesis_id)
            qualification = await _latest_qualification(session, hypothesis_id)
            verified_prospect = (
                await session.execute(
                    text(
                        """
                        SELECT id FROM prospect_resolution_records
                        WHERE hypothesis_id = :hypothesis_id
                          AND party_role = 'INJURED_PARTY'
                          AND stage = 'VERIFIED'
                        ORDER BY updated_at DESC
                        LIMIT 1
                        """
                    ),
                    {"hypothesis_id": hypothesis_id},
                )
            ).mappings().first()
            verified_contact = None
            if verified_prospect:
                verified_contact = (
                    await session.execute(
                        text(
                            """
                            SELECT 1 FROM contact_points
                            WHERE hypothesis_id = :hypothesis_id
                              AND prospect_id = :prospect_id
                              AND verified = true
                              AND verification_confidence >= 0.90
                              AND status = 'ACTIVE'
                            LIMIT 1
                            """
                        ),
                        {
                            "hypothesis_id": hypothesis_id,
                            "prospect_id": verified_prospect["id"],
                        },
                    )
                ).first()

            allowed = _outreach_ready(qualification, gate, verified_prospect, verified_contact)
            if not qualification:
                reasons.append("no lead qualification exists")
            elif not qualification["isCurrent"]:
                reasons.append("lead qualification is stale for the current hypothesis revision")
            elif not qualification["caseQualified"] or qualification["stage"] != "S3_RESOLVED_PROSPECT":
                reasons.append("lead is not a qualified S3 resolved prospect")
            if gate["contactEligibilityStatus"] != "Eligible":
                reasons.append("compliance gate not eligible")
            if not verified_prospect:
                reasons.append("no VERIFIED injured-party prospect")
            if not verified_contact:
                reasons.append("no >=90% verified active contact for the injured-party prospect")

            await session.execute(
                text(
                    """
                    INSERT INTO outreach_activation_attempts (
                        id, hypothesis_id, requested_by, allowed, reason,
                        gate_snapshot_json, created_at
                    ) VALUES (
                        :id, :hypothesis_id, :requested_by, :allowed,
                        :reason, CAST(:gate AS jsonb), now()
                    )
                    """
                ),
                {
                    "id": attempt_id,
                    "hypothesis_id": hypothesis_id,
                    "requested_by": actor.name,
                    "allowed": allowed,
                    "reason": "; ".join(reasons) if reasons else "all gates passed",
                    "gate": json.dumps({"gate": gate, "qualification": qualification}),
                },
            )
            await append_ledger_entry(
                session,
                entry_type="ComplianceDecision",
                subject_id=hypothesis_id,
                payload={
                    "action": "outreach-activation-attempt",
                    "attemptId": attempt_id,
                    "requestedBy": actor.name,
                    "allowed": allowed,
                    "reasons": reasons,
                    "qualification": qualification,
                },
                produced_by=f"human:{actor.name}",
                source_system="PostgreSQL/PostGIS compliance gate",
            )

    if not allowed:
        raise HTTPException(
            403,
            {"status": "BLOCKED", "reasons": reasons, "attemptId": attempt_id},
        )
    return {"status": "ACTIVATED_FOR_ATTORNEY_OUTREACH", "attemptId": attempt_id}
