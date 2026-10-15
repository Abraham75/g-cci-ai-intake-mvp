from __future__ import annotations

from fastapi import HTTPException, Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from .config import settings
from .security import Actor, resolve_bearer


PUBLIC_HEALTH_PATHS = {"/health", "/health/live", "/health/ready"}


def _allowed(actor: Actor, request: Request) -> bool:
    if actor.role == "ADMIN":
        return True

    method = request.method.upper()
    path = request.url.path

    if method == "POST" and path in {"/events/ingest", "/events/ingest-batch", "/cameras/ingest-batch"}:
        return actor.role == "SERVICE"

    if method == "POST" and path == "/correlate":
        return actor.role in {"SERVICE", "INVESTIGATOR", "ATTORNEY"}

    if method == "POST" and path.endswith("/cameras/refresh"):
        return actor.role in {"INVESTIGATOR", "ATTORNEY", "SERVICE"}

    # Feedback and benchmark labels are privileged human judgments.
    # A service token or read-only auditor must never forge attorney ground truth.
    if path.startswith("/validation/benchmark-cases"):
        if method == "GET":
            return actor.role in {"ATTORNEY", "INVESTIGATOR", "AUDITOR"}
        return actor.role == "ATTORNEY"

    if path == "/validation/metrics" or path == "/opportunities":
        return actor.role in {"ATTORNEY", "INVESTIGATOR", "AUDITOR"}

    if path.endswith("/attorney-review") and method == "POST":
        return actor.role == "ATTORNEY"
    if path.endswith("/attorney-reviews") and method == "GET":
        return actor.role in {"ATTORNEY", "INVESTIGATOR", "AUDITOR"}
    if path.endswith("/outcomes") and method == "POST":
        return actor.role == "ATTORNEY"

    if path == "/metrics":
        return actor.role in {"AUDITOR", "SERVICE"}

    # Route-level dependencies further restrict prospect, compliance, contact-vault,
    # and outreach mutations. This middleware supplies the service-wide baseline.
    return actor.role in {"SERVICE", "INVESTIGATOR", "ATTORNEY", "COMPLIANCE", "AUDITOR"}


class GCCIAuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if not settings.require_auth or request.url.path in PUBLIC_HEALTH_PATHS:
            return await call_next(request)

        try:
            actor = resolve_bearer(request.headers.get("authorization"))
        except HTTPException as exc:
            return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})

        if not _allowed(actor, request):
            return JSONResponse(
                status_code=403,
                content={"detail": f"Role '{actor.role}' is not authorized for this operation"},
            )

        request.state.actor = actor
        return await call_next(request)
