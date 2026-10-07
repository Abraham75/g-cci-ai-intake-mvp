from __future__ import annotations

import json
import logging
import time
from uuid import uuid4

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware


log = logging.getLogger("gcci.http")


class RequestContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get("x-request-id") or str(uuid4())
        started = time.perf_counter()
        try:
            response = await call_next(request)
        except Exception:
            duration_ms = round((time.perf_counter() - started) * 1000, 2)
            log.exception(
                json.dumps(
                    {
                        "event": "http_request_failed",
                        "requestId": request_id,
                        "method": request.method,
                        "path": request.url.path,
                        "durationMs": duration_ms,
                    }
                )
            )
            raise

        duration_ms = round((time.perf_counter() - started) * 1000, 2)
        response.headers["X-Request-ID"] = request_id
        actor = getattr(request.state, "actor", None)
        log.info(
            json.dumps(
                {
                    "event": "http_request",
                    "requestId": request_id,
                    "method": request.method,
                    "path": request.url.path,
                    "status": response.status_code,
                    "durationMs": duration_ms,
                    "actorRole": getattr(actor, "role", None),
                    "actorName": getattr(actor, "name", None),
                }
            )
        )
        return response
