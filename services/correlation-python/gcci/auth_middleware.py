from __future__ import annotations

from fastapi import HTTPException, Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from .config import settings
from .security import resolve_bearer


PUBLIC_HEALTH_PATHS = {"/health", "/health/live", "/health/ready"}


class GCCIAuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if not settings.require_auth or request.url.path in PUBLIC_HEALTH_PATHS:
            return await call_next(request)

        try:
            actor = resolve_bearer(request.headers.get("authorization"))
        except HTTPException as exc:
            return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})

        request.state.actor = actor
        return await call_next(request)
