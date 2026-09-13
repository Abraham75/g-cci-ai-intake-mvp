from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from uuid import uuid4

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from .database import DecisionLedgerRow, ScoreJobRow, ScoreResultRow
from .ledger import append_ledger_entry


LEAD_QUALIFICATION_MODEL_VERSION = "gcci-lead-qualification-v1.0.0"
RESOLUTION_PRIORITY_MODEL_VERSION = "gcci-prospect-resolution-v1.0.0"

STAGE_SCORE = {
    "UNKNOWN": 0.0,
    "CANDIDATE": 0.25,
    "CORROBORATED": 0.65,
    "VERIFIED": 1.0,
}


@dataclass(frozen=True)
class ResolutionTaskTemplate:
    task_type: str
    source_type: str
    question: str
    recommended_action: str
    probability_exists: float
    probability_resolves: float
    source_reliability: float
    lawful_access_factor: float
    urgency: float


RESOLUTION_TASKS: tuple[ResolutionTaskTemplate, ...] = (
    ResolutionTaskTemplate(
        task_type="CLAIMANT_IDENTITY",
        source_type="OFFICIAL_CRASH_REPORT",
        question="Can an official crash record verify the injured party role and identity?",
        recommended_action="Obtain the complete official crash report through an approved lawful-access workflow and verify the injured-party role against the incident evidence.",
        probability_exists=0.95,
        probability_resolves=0.95,
        source_reliability=0.95,
        lawful_access_factor=0.85,
        urgency=0.85,
    ),
    ResolutionTaskTemplate(
        task_type="CLAIMANT_CORROBORATION",
        source_type="CAD_911_RECORD",
        question="Can CAD/911 records corroborate occupant role, transport, or incident participation?",
        recommended_action="Request the incident-level CAD/911 record where legally available and use it only to corroborate facts supported by the record.",
        probability_exists=0.85,
        probability_resolves=0.55,
        source_reliability=0.85,
        lawful_access_factor=0.85,
        urgency=0.70,
    ),
    ResolutionTaskTemplate(
        task_type="CLAIMANT_CORROBORATION",
        source_type="TOW_RECOVERY_RECORD",
        question="Can a tow/recovery record corroborate the involved vehicle and responsible custodian?",
        recommended_action="Identify the responding tow/recovery provider and obtain an authorized record linking the involved vehicle to the incident.",
        probability_exists=0.70,
        probability_resolves=0.45,
        source_reliability=0.75,
        lawful_access_factor=0.75,
        urgency=0.55,
    ),
    ResolutionTaskTemplate(
        task_type="CLAIMANT_CORROBORATION",
        source_type="PUBLIC_COURT_OR_AGENCY_RECORD",
        question="Does a lawful public filing or agency record independently corroborate the claimant identity?",
        recommended_action="Search counsel-approved public court or agency sources for an independent corroborating record. Do not treat fuzzy-name similarity as verification.",
        probability_exists=0.35,
        probability_resolves=0.40,
        source_reliability=0.80,
        lawful_access_factor=0.70,
        urgency=0.35,
    ),
    ResolutionTaskTemplate(
        task_type="CLAIMANT_CORROBORATION",
        source_type="EXISTING_CASE_WITNESS_LINKAGE",
        question="Can an existing client, witness, or case record lawfully corroborate the injured party?",
        recommended_action="Check existing firm case/witness records for a direct, evidence-backed relationship to this incident. Never infer identity from proximity alone.",
        probability_exists=0.45,
        probability_resolves=0.35,
        source_reliability=0.75,
        lawful_access_factor=0.85,
        urgency=0.50,
    ),
)


def _clamp(value: float) -> float:
    return max(0.0, min(1.0, value))


def _priority(template: ResolutionTaskTemplate) -> float:
    value = (
        template.probability_exists
        * template.probability_resolves
        * template.source_reliability
        * template.lawful_access_factor
        * (0.60 + 0.40 * template.urgency)
    )
    return round(_clamp(value), 4)


def _canonical_input(job: ScoreJobRow) -> dict[str, Any]:
    return dict(job.score_input_json.get("canonicalInput") or {})


def _canonical_result(score_result: ScoreResultRow) -> dict[str, Any]:
    envelope = score_result.result_json or {}
    return dict(envelope.get("result") or {})


async def _current_claimant_resolution(session: AsyncSession, hypothesis_id: str) -> dict[str, Any]:
    row = (
        await session.execute(
            text(
                """
                SELECT id, party_role, stage, display_label, source_type, source_reference,
                       confidence, verified, lawful_access_basis, notes_json, updated_at
                FROM prospect_resolution_records
                WHERE hypothesis_id = :hypothesis_id
                  AND party_role = 'INJURED_PARTY'
                ORDER BY verified DESC, confidence DESC, updated_at DESC
                LIMIT 1
                """
            ),
            {"hypothesis_id": hypothesis_id},
        )
    ).mappings().first()
    if row is None:
        return {
            "stage": "UNKNOWN",
            "score": 0.0,
            "verified": False,
            "record": None,
        }
    stage = str(row["stage"])
    return {
        "stage": stage,
        "score": STAGE_SCORE.get(stage, 0.0),
        "verified": bool(row["verified"]) and stage == "VERIFIED",
        "record": {
            "id": row["id"],
            "partyRole": row["party_role"],
            "stage": stage,
            "displayLabel": row["display_label"],
            "sourceType": row["source_type"],
            "sourceReference": row["source_reference"],
            "confidence": float(row["confidence"]),
            "verified": bool(row["verified"]),
            "lawfulAccessBasis": row["lawful_access_basis"],
            "notes": row["notes_json"],
            "updatedAt": row["updated_at"].isoformat(),
        },
    }


def _qualification_decision(
    *,
    score: float,
    tier: str,
    canonical_input: dict[str, Any],
    claimant_stage: str,
) -> dict[str, Any]:
    scores = canonical_input.get("scores") or {}
    liability = float(scores.get("liability") or 0.0)
    injury = float(scores.get("injury") or 0.0)
    collectability = float(scores.get("collectability") or 0.0)
    evidence = float(scores.get("evidence") or 0.0)
    defendant_resolution = float(scores.get("defendantResolution") or 0.0)
    contradictions = canonical_input.get("contradictions") or {}
    high_contradictions = int(contradictions.get("highSeverityUnresolved") or 0)

    qualification_score = _clamp(
        0.30 * score
        + 0.20 * injury
        + 0.20 * liability
        + 0.15 * collectability
        + 0.10 * evidence
        + 0.05 * defendant_resolution
    )

    reasons: list[str] = []
    blockers: list[str] = []
    required_actions: list[str] = []

    if injury >= 0.60:
        reasons.append("Strong injury-severity signal supports attorney review.")
    elif injury >= 0.35:
        reasons.append("Meaningful injury signal is present but should be further corroborated.")
    else:
        blockers.append("Injury signal is below the qualified-case threshold.")
        required_actions.append("Obtain stronger injury/transport/severity evidence.")

    if liability >= 0.60:
        reasons.append("Strong liability signal is present.")
    elif liability >= 0.35:
        reasons.append("Meaningful liability signal is present but remains incomplete.")
    else:
        blockers.append("Liability evidence is below the qualified-case threshold.")
        required_actions.append("Develop crash-mechanism, citation, witness, or carrier-fault evidence.")

    if collectability >= 0.55:
        reasons.append("Commercial collectability signal is sufficient for qualification.")
    else:
        blockers.append("Commercial collectability or carrier resolution is incomplete.")
        required_actions.append("Resolve motor carrier/USDOT/coverage indicators before qualification.")

    if evidence < 0.25:
        blockers.append("Independent evidence support is too thin for a qualified case.")
        required_actions.append("Acquire an additional independent evidence source.")

    if high_contradictions > 0:
        blockers.append("An unresolved high-severity contradiction prevents qualified-case status.")
        required_actions.append("Resolve the high-severity contradiction with source evidence and human adjudication.")

    strong_path = score >= 0.65
    exceptional_path = score >= 0.55 and injury >= 0.60 and liability >= 0.60 and collectability >= 0.55
    minimum_gates = injury >= 0.35 and liability >= 0.35 and collectability >= 0.45 and evidence >= 0.25
    case_qualified = (strong_path or exceptional_path) and minimum_gates and high_contradictions == 0

    if case_qualified:
        reasons.append("Case-opportunity and minimum evidentiary gates satisfy the qualified-case policy.")

    if score < 0.45:
        stage = "S0_SIGNAL"
    elif not case_qualified:
        stage = "S1_OPPORTUNITY"
    elif claimant_stage != "VERIFIED":
        stage = "S2_QUALIFIED_CASE"
        required_actions.append("Resolve the injured party to VERIFIED using authoritative evidence.")
    else:
        stage = "S3_RESOLVED_PROSPECT"
        reasons.append("Injured-party identity has reached VERIFIED resolution stage.")
        required_actions.append("Run the independent compliance gate before any outreach activation.")

    return {
        "stage": stage,
        "qualificationScore": round(qualification_score, 4),
        "caseQualified": case_qualified,
        "dimensions": {
            "caseOpportunityScore": round(score, 4),
            "tier": tier,
            "injury": round(injury, 4),
            "liability": round(liability, 4),
            "collectability": round(collectability, 4),
            "evidence": round(evidence, 4),
            "defendantResolution": round(defendant_resolution, 4),
            "highSeverityUnresolvedContradictions": high_contradictions,
        },
        "reasons": reasons,
        "blockers": blockers,
        "requiredActions": list(dict.fromkeys(required_actions)),
    }


async def _replace_resolution_tasks(
    session: AsyncSession,
    *,
    hypothesis_id: str,
    revision: int,
    claimant_stage: str,
) -> list[dict[str, Any]]:
    await session.execute(
        text(
            """
            UPDATE resolution_tasks
            SET status = 'SUPERSEDED', updated_at = now()
            WHERE hypothesis_id = :hypothesis_id
              AND revision < :revision
              AND status = 'OPEN'
            """
        ),
        {"hypothesis_id": hypothesis_id, "revision": revision},
    )
    await session.execute(
        text("DELETE FROM resolution_tasks WHERE hypothesis_id = :hypothesis_id AND revision = :revision"),
        {"hypothesis_id": hypothesis_id, "revision": revision},
    )

    if claimant_stage == "VERIFIED":
        return []

    tasks: list[dict[str, Any]] = []
    for template in RESOLUTION_TASKS:
        task_id = str(uuid4())
        priority = _priority(template)
        await session.execute(
            text(
                """
                INSERT INTO resolution_tasks (
                    id, hypothesis_id, revision, task_type, source_type, question,
                    recommended_action, probability_exists, probability_resolves,
                    source_reliability, lawful_access_factor, urgency,
                    resolution_priority_score, status, model_version
                ) VALUES (
                    :id, :hypothesis_id, :revision, :task_type, :source_type, :question,
                    :recommended_action, :probability_exists, :probability_resolves,
                    :source_reliability, :lawful_access_factor, :urgency,
                    :priority, 'OPEN', :model_version
                )
                """
            ),
            {
                "id": task_id,
                "hypothesis_id": hypothesis_id,
                "revision": revision,
                "task_type": template.task_type,
                "source_type": template.source_type,
                "question": template.question,
                "recommended_action": template.recommended_action,
                "probability_exists": template.probability_exists,
                "probability_resolves": template.probability_resolves,
                "source_reliability": template.source_reliability,
                "lawful_access_factor": template.lawful_access_factor,
                "urgency": template.urgency,
                "priority": priority,
                "model_version": RESOLUTION_PRIORITY_MODEL_VERSION,
            },
        )
        tasks.append(
            {
                "id": task_id,
                "taskType": template.task_type,
                "sourceType": template.source_type,
                "question": template.question,
                "recommendedAction": template.recommended_action,
                "probabilityExists": template.probability_exists,
                "probabilityResolves": template.probability_resolves,
                "sourceReliability": template.source_reliability,
                "lawfulAccessFactor": template.lawful_access_factor,
                "urgency": template.urgency,
                "resolutionPriorityScore": priority,
                "status": "OPEN",
            }
        )
    tasks.sort(key=lambda item: item["resolutionPriorityScore"], reverse=True)
    return tasks


async def build_lead_qualification_for_score(
    session: AsyncSession,
    *,
    score_result: ScoreResultRow,
    score_ledger_entry_id: str | None = None,
) -> dict[str, Any]:
    job = (
        await session.execute(
            select(ScoreJobRow).where(
                ScoreJobRow.hypothesis_id == score_result.hypothesis_id,
                ScoreJobRow.revision == score_result.revision,
            )
        )
    ).scalar_one()
    canonical_input = _canonical_input(job)
    canonical_result = _canonical_result(score_result)
    resolution = await _current_claimant_resolution(session, score_result.hypothesis_id)
    decision = _qualification_decision(
        score=score_result.score,
        tier=score_result.tier,
        canonical_input=canonical_input,
        claimant_stage=resolution["stage"],
    )
    tasks = await _replace_resolution_tasks(
        session,
        hypothesis_id=score_result.hypothesis_id,
        revision=score_result.revision,
        claimant_stage=resolution["stage"],
    )

    snapshot_id = str(uuid4())
    await session.execute(
        text(
            """
            INSERT INTO lead_qualification_snapshots (
                id, hypothesis_id, revision, score_result_id, stage,
                qualification_score, case_qualified, claimant_resolution_stage,
                claimant_resolution_score, contact_eligibility, dimensions_json,
                reasons_json, blockers_json, required_actions_json, model_version
            ) VALUES (
                :id, :hypothesis_id, :revision, :score_result_id, :stage,
                :qualification_score, :case_qualified, :claimant_stage,
                :claimant_score, 'NOT_EVALUATED', CAST(:dimensions AS jsonb),
                CAST(:reasons AS jsonb), CAST(:blockers AS jsonb),
                CAST(:required_actions AS jsonb), :model_version
            )
            ON CONFLICT (hypothesis_id, revision) DO UPDATE SET
                score_result_id = EXCLUDED.score_result_id,
                stage = EXCLUDED.stage,
                qualification_score = EXCLUDED.qualification_score,
                case_qualified = EXCLUDED.case_qualified,
                claimant_resolution_stage = EXCLUDED.claimant_resolution_stage,
                claimant_resolution_score = EXCLUDED.claimant_resolution_score,
                contact_eligibility = 'NOT_EVALUATED',
                dimensions_json = EXCLUDED.dimensions_json,
                reasons_json = EXCLUDED.reasons_json,
                blockers_json = EXCLUDED.blockers_json,
                required_actions_json = EXCLUDED.required_actions_json,
                model_version = EXCLUDED.model_version
            """
        ),
        {
            "id": snapshot_id,
            "hypothesis_id": score_result.hypothesis_id,
            "revision": score_result.revision,
            "score_result_id": score_result.id,
            "stage": decision["stage"],
            "qualification_score": decision["qualificationScore"],
            "case_qualified": decision["caseQualified"],
            "claimant_stage": resolution["stage"],
            "claimant_score": resolution["score"],
            "dimensions": __import__("json").dumps(decision["dimensions"]),
            "reasons": __import__("json").dumps(decision["reasons"]),
            "blockers": __import__("json").dumps(decision["blockers"]),
            "required_actions": __import__("json").dumps(decision["requiredActions"]),
            "model_version": LEAD_QUALIFICATION_MODEL_VERSION,
        },
    )

    entry = await append_ledger_entry(
        session,
        entry_type="LeadQualification",
        subject_id=score_result.hypothesis_id,
        payload={
            "action": "lead-qualified",
            "hypothesisRevision": score_result.revision,
            "scoreResultId": score_result.id,
            "stage": decision["stage"],
            "qualificationScore": decision["qualificationScore"],
            "caseQualified": decision["caseQualified"],
            "claimantResolutionStage": resolution["stage"],
            "claimantResolutionScore": resolution["score"],
            "contactEligibility": "NOT_EVALUATED",
            "dimensions": decision["dimensions"],
            "reasons": decision["reasons"],
            "blockers": decision["blockers"],
            "requiredActions": decision["requiredActions"],
            "resolutionTaskIds": [task["id"] for task in tasks],
            "policy": {
                "identityInferredFromWeakCorrelation": False,
                "contactEligibilityEvaluated": False,
                "requiresIndependentComplianceGate": True,
            },
        },
        produced_by="ai.leadQualification",
        source_system="Python:lead_qualification.py",
        model_version=LEAD_QUALIFICATION_MODEL_VERSION,
        input_entry_ids=[score_ledger_entry_id] if score_ledger_entry_id else [],
    )

    for task in tasks:
        await append_ledger_entry(
            session,
            entry_type="ProspectResolutionTask",
            subject_id=score_result.hypothesis_id,
            payload={
                "action": "resolution-source-ranked",
                "hypothesisRevision": score_result.revision,
                **task,
                "policy": {
                    "taskMayGuideSourceAcquisition": True,
                    "taskMayAssertIdentity": False,
                    "contactEligibilityEvaluated": False,
                },
            },
            produced_by="ai.prospectResolution",
            source_system="Python:lead_qualification.py",
            model_version=RESOLUTION_PRIORITY_MODEL_VERSION,
            input_entry_ids=[entry.id],
        )

    return {
        **decision,
        "hypothesisId": score_result.hypothesis_id,
        "revision": score_result.revision,
        "scoreResultId": score_result.id,
        "claimantResolution": resolution,
        "resolutionTasks": tasks,
        "canonicalScore": canonical_result,
        "contactEligibility": "NOT_EVALUATED",
        "modelVersion": LEAD_QUALIFICATION_MODEL_VERSION,
    }


async def latest_lead_qualification(session: AsyncSession, hypothesis_id: str) -> dict[str, Any] | None:
    row = (
        await session.execute(
            text(
                """
                SELECT id, hypothesis_id, revision, score_result_id, stage,
                       qualification_score, case_qualified, claimant_resolution_stage,
                       claimant_resolution_score, contact_eligibility, dimensions_json,
                       reasons_json, blockers_json, required_actions_json, model_version, created_at
                FROM lead_qualification_snapshots
                WHERE hypothesis_id = :hypothesis_id
                ORDER BY revision DESC
                LIMIT 1
                """
            ),
            {"hypothesis_id": hypothesis_id},
        )
    ).mappings().first()
    if row is None:
        return None
    return {
        "id": row["id"],
        "hypothesisId": row["hypothesis_id"],
        "revision": row["revision"],
        "scoreResultId": row["score_result_id"],
        "stage": row["stage"],
        "qualificationScore": float(row["qualification_score"]),
        "caseQualified": bool(row["case_qualified"]),
        "claimantResolutionStage": row["claimant_resolution_stage"],
        "claimantResolutionScore": float(row["claimant_resolution_score"]),
        "contactEligibility": row["contact_eligibility"],
        "dimensions": row["dimensions_json"],
        "reasons": row["reasons_json"],
        "blockers": row["blockers_json"],
        "requiredActions": row["required_actions_json"],
        "modelVersion": row["model_version"],
        "createdAt": row["created_at"].isoformat(),
    }


async def resolution_tasks_for_hypothesis(
    session: AsyncSession,
    hypothesis_id: str,
    *,
    open_only: bool = False,
) -> list[dict[str, Any]]:
    condition = "AND status = 'OPEN'" if open_only else ""
    rows = (
        await session.execute(
            text(
                f"""
                SELECT id, revision, task_type, source_type, question, recommended_action,
                       probability_exists, probability_resolves, source_reliability,
                       lawful_access_factor, urgency, resolution_priority_score,
                       status, model_version, created_at, updated_at
                FROM resolution_tasks
                WHERE hypothesis_id = :hypothesis_id
                {condition}
                ORDER BY revision DESC, resolution_priority_score DESC
                """
            ),
            {"hypothesis_id": hypothesis_id},
        )
    ).mappings().all()
    return [
        {
            "id": row["id"],
            "revision": row["revision"],
            "taskType": row["task_type"],
            "sourceType": row["source_type"],
            "question": row["question"],
            "recommendedAction": row["recommended_action"],
            "probabilityExists": float(row["probability_exists"]),
            "probabilityResolves": float(row["probability_resolves"]),
            "sourceReliability": float(row["source_reliability"]),
            "lawfulAccessFactor": float(row["lawful_access_factor"]),
            "urgency": float(row["urgency"]),
            "resolutionPriorityScore": float(row["resolution_priority_score"]),
            "status": row["status"],
            "modelVersion": row["model_version"],
            "createdAt": row["created_at"].isoformat(),
            "updatedAt": row["updated_at"].isoformat(),
        }
        for row in rows
    ]
