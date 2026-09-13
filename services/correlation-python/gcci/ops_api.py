from __future__ import annotations

import time

import httpx
from fastapi import APIRouter, HTTPException
from sqlalchemy import text

from .config import settings
from .database import SessionLocal

router = APIRouter(tags=["operations"])


def _runtime_base() -> str:
    suffix = "/api/scoring/score"
    url = settings.canonical_scorer_url.rstrip("/")
    return url[: -len(suffix)] if url.endswith(suffix) else url.rsplit("/api/", 1)[0]


async def _runtime_get(path: str) -> dict:
    headers: dict[str, str] = {}
    if settings.internal_service_token:
        headers["Authorization"] = f"Bearer {settings.internal_service_token}"
    timeout = httpx.Timeout(settings.canonical_scorer_timeout_seconds)
    async with httpx.AsyncClient(timeout=timeout) as client:
        response = await client.get(f"{_runtime_base()}{path}", headers=headers)
        response.raise_for_status()
        return response.json()


@router.get("/health/live")
async def live() -> dict:
    return {
        "status": "ok",
        "service": "gcci-cross-source-correlation",
        "version": "1.6.0",
    }


@router.get("/health/ready")
async def ready() -> dict:
    """Load-balancer readiness: database connectivity and required schema only."""
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
                          to_regclass('public.traffic_cameras') IS NOT NULL AS cameras,
                          to_regclass('public.schema_migrations') IS NOT NULL AS migrations
                        """
                    )
                )
            ).mappings().one()
    except Exception as exc:
        if settings.environment.lower() == "production":
            raise HTTPException(503, {"status": "not-ready"}) from exc
        raise HTTPException(503, {"status": "not-ready", "error": str(exc)[:500]}) from exc

    if not all(bool(value) for value in schema.values()):
        if settings.environment.lower() == "production":
            raise HTTPException(503, {"status": "not-ready"})
        raise HTTPException(503, {"status": "not-ready", "schema": dict(schema)})
    return {"status": "ready"}


@router.get("/health/dependencies")
async def dependency_health() -> dict:
    """Operational dependency status. Failure does not evict an otherwise healthy API pod."""
    started = time.perf_counter()
    scorer_ok = False
    scorer_error = None
    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(3.0)) as client:
            response = await client.get(f"{_runtime_base()}/health/live")
            scorer_ok = response.is_success
            if not scorer_ok:
                scorer_error = f"HTTP {response.status_code}"
    except Exception as exc:
        scorer_error = type(exc).__name__

    async with SessionLocal() as session:
        camera = (
            await session.execute(
                text(
                    """
                    SELECT count(*) FILTER (WHERE active = true) AS active,
                           max(last_seen_at) AS last_seen
                    FROM traffic_cameras
                    """
                )
            )
        ).mappings().one()
        failed_jobs = (
            await session.execute(text("SELECT count(*) FROM score_jobs WHERE status = 'FAILED'"))
        ).scalar_one()

    return {
        "status": "ok" if scorer_ok else "degraded",
        "canonicalScorer": {"ok": scorer_ok, "error": scorer_error},
        "cameraInventory": {
            "active": int(camera["active"] or 0),
            "lastSeenAt": camera["last_seen"].isoformat() if camera["last_seen"] else None,
        },
        "failedScoreJobs": int(failed_jobs or 0),
        "checkedInMs": round((time.perf_counter() - started) * 1000, 2),
    }


@router.get("/runtime/ontology")
async def runtime_ontology() -> dict:
    try:
        return await _runtime_get("/api/ontology")
    except Exception as exc:
        raise HTTPException(502, "Canonical runtime ontology endpoint unavailable") from exc


@router.get("/signals/live")
async def live_signals_proxy() -> dict:
    """Proxy the public incident-signal analyzer through the authenticated API boundary."""
    try:
        return await _runtime_get("/api/signals/live")
    except Exception as exc:
        raise HTTPException(502, "Live signal runtime unavailable") from exc


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
