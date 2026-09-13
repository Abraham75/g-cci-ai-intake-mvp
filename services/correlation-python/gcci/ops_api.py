from __future__ import annotations

from fastapi import APIRouter, HTTPException
from sqlalchemy import text

from .config import settings
from .database import SessionLocal
from .ledger import verify_ledger_chain


router = APIRouter(tags=["operations"])


@router.get("/health/live")
async def live() -> dict:
    return {
        "status": "ok",
        "service": "gcci-cross-source-correlation",
        "version": "1.5.0",
        "environment": settings.environment,
    }


@router.get("/health/ready")
async def ready() -> dict:
    checks: dict[str, object] = {}
    try:
        async with SessionLocal() as session:
            await session.execute(text("SELECT 1"))
            checks["database"] = "ok"
            valid, error = await verify_ledger_chain(session)
            checks["decisionLedger"] = "ok" if valid else {"status": "invalid", "error": error}
            migration = (
                await session.execute(
                    text(
                        """
                        SELECT to_regclass('public.compliance_gate_states') IS NOT NULL AS compliance,
                               to_regclass('public.contact_points') IS NOT NULL AS contacts,
                               to_regclass('public.lead_qualification_snapshots') IS NOT NULL AS leads
                        """
                    )
                )
            ).mappings().one()
            checks["schema"] = {
                "compliance": bool(migration["compliance"]),
                "contacts": bool(migration["contacts"]),
                "leadQualification": bool(migration["leads"]),
            }
    except Exception as exc:
        raise HTTPException(503, {"status": "not-ready", "error": str(exc)[:500]}) from exc

    schema_ok = all(checks["schema"].values())
    ledger_ok = checks["decisionLedger"] == "ok"
    if not schema_ok or not ledger_ok:
        raise HTTPException(503, {"status": "not-ready", "checks": checks})
    return {"status": "ready", "checks": checks}


@router.get("/metrics")
async def metrics() -> dict:
    """Operational counters suitable for scraping/adaptation by a metrics collector."""
    async with SessionLocal() as session:
        row = (
            await session.execute(
                text(
                    """
                    SELECT
                      (SELECT count(*) FROM score_jobs WHERE status IN ('PENDING','FAILED','PROCESSING')) AS score_jobs_open,
                      (SELECT count(*) FROM evidence_acquisition_tasks WHERE status = 'OPEN') AS evidence_tasks_open,
                      (SELECT count(*) FROM resolution_tasks WHERE status = 'OPEN') AS resolution_tasks_open,
                      (SELECT count(*) FROM lead_qualification_snapshots WHERE case_qualified = true) AS qualified_cases,
                      (SELECT count(*) FROM compliance_gate_states WHERE contact_eligibility_status = 'Eligible') AS contact_eligible,
                      (SELECT count(*) FROM contact_points WHERE status = 'ACTIVE' AND verified = true) AS verified_contacts
                    """
                )
            )
        ).mappings().one()
    return {key: int(value or 0) for key, value in row.items()}
