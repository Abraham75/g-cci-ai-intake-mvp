from __future__ import annotations

import secrets
from dataclasses import dataclass

from fastapi import Depends, Header, HTTPException, status

from .config import settings


@dataclass(frozen=True)
class Actor:
    name: str
    role: str


def _resolve_bearer(authorization: str | None) -> Actor:
    if not settings.require_auth:
        return Actor(name="development-bypass", role="ADMIN")

    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Bearer token required",
        )

    supplied = authorization.split(" ", 1)[1].strip()
    for token, identity in settings.auth_tokens.items():
        if secrets.compare_digest(supplied, token):
            if ":" not in identity:
                raise HTTPException(status_code=500, detail="Invalid server auth configuration")
            role, name = identity.split(":", 1)
            return Actor(name=name, role=role.upper())

    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid bearer token")


async def current_actor(authorization: str | None = Header(default=None)) -> Actor:
    return _resolve_bearer(authorization)


def require_roles(*roles: str):
    allowed = {role.upper() for role in roles}

    async def dependency(actor: Actor = Depends(current_actor)) -> Actor:
        if actor.role not in allowed and actor.role != "ADMIN":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role '{actor.role}' is not authorized for this operation",
            )
        return actor

    return dependency
