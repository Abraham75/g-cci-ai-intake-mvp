from __future__ import annotations

from fastapi import APIRouter, HTTPException
from sqlalchemy import text

from .config import settings
from .database import SessionLocal


router = APIRouter(tags=["operations"])


@router.get("/health/live")
async def live() -> dict:
    return {
        "status": "ok",
        "service": "gcci-cross-source-correlation",
        "version": "1.5.0",
    }


@router.get("/health/ready")
async def ready() -> dict:
    """Cheap load-balancer readiness check; full ledger verification is separate."""
    try:
        async with SessionLocal() as session:
            await session.execute(text("SELECT 1"))
            schema = (
                await session.execute(
                    text(
                        """
                        SELECT
                          to_regclass('public.decision_ledger') IS NOT NULL AS ledger,
                          to_regclass('public.compliance_gate_states') IS NOT NULL AS compliance,
                          to_regclass('public.contact_points') IS NOT NULL AS contacts,
                          to_regclass('public.lead_qualification_snapshots') IS NOT NULL AS leads,
                          to_regclass('public.traffic_cameras') IS NOT NULL AS cameras
                        """
                    )
                )
            ).mappings().one()
    except Exception as exc:
        if settings.environment.lower() == "production":
            raise HTTPException(503, {"status": "not-ready"}) from exc
        raise HTTPException(503, {"status": "not-ready", "error": str(exc)[:500]}) from exc

    schema_ok = all(bool(value) for value in schema.values())
    if not schema_ok:
        if settings.environment.lower() == "production":
            raise HTTPException(503, {"status": "not-ready"})
        raise HTTPException(503, {"status": "not-ready", "schema": dict(schema)})
    return {"status": "ready"}


@router.get("/metrics")
async def metrics() -> dict:
    """Operational counters for an authenticated metrics collector."""
    async with SessionLocal() as session:
        row = (
            await session.execute(
                text(
                    """
                    SELECT
                      (SELECT count(*) FROM score_jobs WHERE status IN ('PENDING','FAILED','PROCESSING')) AS score_jobs_open,
                      (SELECT count(*) FROM score_jobs WHERE status = 'FAILED') AS score_jobs_failed,
                      (SELECT count(*) FROM evidence_acquisition_tasks WHERE status = 'OPEN') AS evidence_tasks_open,
                      (SELECT count(*) FROM resolution_tasks WHERE status = 'OPEN') AS resolution_tasks_open,
                      (SELECT count(*) FROM lead_qualification_snapshots WHERE case_qualified = true) AS qualified_cases,
                      (SELECT count(*) FROM compliance_gate_states WHERE contact_eligibility_status = 'Eligible') AS contact_eligible,
                      (SELECT count(*) FROM contact_points WHERE status = 'ACTIVE' AND verified = true) AS verified_contacts,
                      (SELECT count(*) FROM outreach_activation_attempts WHERE allowed = false) AS blocked_activation_attempts
                    """
                )
            )
        ).mappings().one()
    return {key: int(value or 0) for key, value in row.items()}
