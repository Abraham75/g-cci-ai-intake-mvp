from __future__ import annotations

import secrets
from dataclasses import dataclass
from functools import lru_cache
from typing import Any

import jwt
from fastapi import Depends, Header, HTTPException, status
from jwt import PyJWKClient

from .config import settings


@dataclass(frozen=True)
class Actor:
    name: str
    role: str


_ALLOWED_ROLES = {"SERVICE", "INVESTIGATOR", "ATTORNEY", "COMPLIANCE", "AUDITOR", "ADMIN"}


def _static_actor(supplied: str) -> Actor | None:
    for token, identity in settings.auth_tokens.items():
        if not secrets.compare_digest(supplied, token):
            continue
        if ":" not in identity:
            raise HTTPException(status_code=500, detail="Invalid server auth configuration")
        role, name = identity.split(":", 1)
        role = role.upper()
        if role not in _ALLOWED_ROLES or not name:
            raise HTTPException(status_code=500, detail="Invalid server auth configuration")
        return Actor(name=name, role=role)
    return None


@lru_cache(maxsize=1)
def _jwk_client() -> PyJWKClient | None:
    if not settings.oidc_jwks_url:
        return None
    return PyJWKClient(settings.oidc_jwks_url, cache_keys=True, lifespan=300)


def _claim_path(claims: dict[str, Any], path: str) -> Any:
    value: Any = claims
    for part in path.split("."):
        if not isinstance(value, dict):
            return None
        value = value.get(part)
    return value


def _select_role(raw: Any) -> str | None:
    candidates: list[str]
    if isinstance(raw, str):
        candidates = [raw]
    elif isinstance(raw, list):
        candidates = [str(item) for item in raw]
    else:
        return None

    normalized = {candidate.upper() for candidate in candidates}
    # Prefer least-privileged recognized application roles over ADMIN when a token
    # carries many IdP roles. Provider-side group->role mapping remains explicit.
    for role in ("AUDITOR", "INVESTIGATOR", "ATTORNEY", "COMPLIANCE", "SERVICE", "ADMIN"):
        if role in normalized:
            return role
    return None


def _oidc_actor(token: str) -> Actor | None:
    if not (settings.oidc_issuer and settings.oidc_audience and settings.oidc_jwks_url):
        return None
    client = _jwk_client()
    if client is None:
        return None
    try:
        signing_key = client.get_signing_key_from_jwt(token)
        claims = jwt.decode(
            token,
            signing_key.key,
            algorithms=settings.oidc_allowed_algorithms,
            audience=settings.oidc_audience,
            issuer=settings.oidc_issuer,
            options={"require": ["exp", "iat", "sub"]},
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired OIDC bearer token",
        ) from exc

    role = _select_role(_claim_path(claims, settings.oidc_role_claim))
    if role is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="OIDC token does not contain an authorized G-CCI role",
        )
    name_value = _claim_path(claims, settings.oidc_name_claim) or claims.get("preferred_username") or claims.get("sub")
    return Actor(name=str(name_value), role=role)


def resolve_bearer(authorization: str | None) -> Actor:
    if not settings.require_auth:
        return Actor(name="development-bypass", role="ADMIN")

    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Bearer token required",
        )

    supplied = authorization.split(" ", 1)[1].strip()
    if not supplied:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Bearer token required")

    static = _static_actor(supplied)
    if static is not None:
        return static
    oidc = _oidc_actor(supplied)
    if oidc is not None:
        return oidc
    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid bearer token")


async def current_actor(authorization: str | None = Header(default=None)) -> Actor:
    return resolve_bearer(authorization)


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
