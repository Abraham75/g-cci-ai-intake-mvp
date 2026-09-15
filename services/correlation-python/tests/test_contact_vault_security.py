from __future__ import annotations

import base64

import pytest
from fastapi import HTTPException

from gcci.config import settings
from gcci.contact_vault import (
    decrypt_contact_value,
    encrypt_contact_value,
    normalize_contact_value,
)
from gcci.security import resolve_bearer


@pytest.fixture
def vault_config(monkeypatch):
    monkeypatch.setattr(
        settings,
        "contact_vault_key_b64",
        base64.b64encode(bytes(range(32))).decode("ascii"),
    )
    monkeypatch.setattr(settings, "contact_fingerprint_key", "unit-test-fingerprint-key")


def test_phone_contact_round_trip_is_encrypted_and_masked(vault_config):
    encrypted, nonce, fingerprint, masked = encrypt_contact_value(
        "PHONE",
        "+1 (404) 555-1212",
        aad="gcci:hyp-1:prospect-1:PHONE",
    )

    assert encrypted != b"14045551212"
    assert len(nonce) == 12
    assert len(fingerprint) == 64
    assert masked == "***-***-1212"
    assert (
        decrypt_contact_value(
            encrypted,
            nonce,
            aad="gcci:hyp-1:prospect-1:PHONE",
        )
        == "14045551212"
    )


def test_contact_ciphertext_is_bound_to_context(vault_config):
    encrypted, nonce, _, _ = encrypt_contact_value(
        "EMAIL",
        "Prospect@Example.com",
        aad="gcci:hyp-1:prospect-1:EMAIL",
    )
    with pytest.raises(Exception):
        decrypt_contact_value(
            encrypted,
            nonce,
            aad="gcci:wrong-hypothesis:prospect-1:EMAIL",
        )


def test_invalid_phone_is_rejected():
    with pytest.raises(ValueError):
        normalize_contact_value("PHONE", "123")


def test_production_bearer_resolution_uses_configured_role(monkeypatch):
    monkeypatch.setattr(settings, "require_auth", True)
    monkeypatch.setattr(settings, "auth_tokens", {"secret-token": "ATTORNEY:alice"})
    actor = resolve_bearer("Bearer secret-token")
    assert actor.role == "ATTORNEY"
    assert actor.name == "alice"


def test_invalid_bearer_is_rejected(monkeypatch):
    monkeypatch.setattr(settings, "require_auth", True)
    monkeypatch.setattr(settings, "auth_tokens", {"secret-token": "ATTORNEY:alice"})
    with pytest.raises(HTTPException) as exc:
        resolve_bearer("Bearer wrong-token")
    assert exc.value.status_code == 401
