from __future__ import annotations

import base64
import hashlib
import hmac
import re

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from .config import settings


def _key() -> bytes:
    if not settings.contact_vault_key_b64:
        raise RuntimeError("Contact vault key is not configured")
    try:
        key = base64.b64decode(settings.contact_vault_key_b64, validate=True)
    except Exception as exc:  # pragma: no cover - defensive configuration guard
        raise RuntimeError("Contact vault key is not valid base64") from exc
    if len(key) != 32:
        raise RuntimeError("Contact vault key must decode to exactly 32 bytes")
    return key


def _fingerprint_key() -> bytes:
    if not settings.contact_fingerprint_key:
        raise RuntimeError("Contact fingerprint key is not configured")
    return settings.contact_fingerprint_key.encode("utf-8")


def normalize_contact_value(contact_type: str, value: str) -> str:
    raw = value.strip()
    kind = contact_type.upper()
    if kind == "PHONE":
        digits = re.sub(r"\D", "", raw)
        if len(digits) < 10 or len(digits) > 15:
            raise ValueError("Phone number must contain 10-15 digits")
        return digits
    if kind == "EMAIL":
        lowered = raw.lower()
        if "@" not in lowered or lowered.startswith("@") or lowered.endswith("@"):
            raise ValueError("Invalid email address")
        return lowered
    if not raw:
        raise ValueError("Contact value cannot be blank")
    return raw


def mask_contact_value(contact_type: str, normalized: str) -> str:
    kind = contact_type.upper()
    if kind == "PHONE":
        return f"***-***-{normalized[-4:]}"
    if kind == "EMAIL":
        local, domain = normalized.split("@", 1)
        visible = local[:1] if local else "*"
        return f"{visible}***@{domain}"
    if kind == "ADDRESS":
        return "[encrypted address]"
    return "[encrypted contact value]"


def fingerprint_contact_value(contact_type: str, normalized: str) -> str:
    material = f"{contact_type.upper()}:{normalized}".encode("utf-8")
    return hmac.new(_fingerprint_key(), material, hashlib.sha256).hexdigest()


def encrypt_contact_value(contact_type: str, value: str, *, aad: str) -> tuple[bytes, bytes, str, str]:
    normalized = normalize_contact_value(contact_type, value)
    nonce = AESGCM.generate_key(bit_length=96)[:12]
    # AESGCM.generate_key only supports 128/192/256 bits. Use os.urandom for nonce.
    import os

    nonce = os.urandom(12)
    cipher = AESGCM(_key())
    encrypted = cipher.encrypt(nonce, normalized.encode("utf-8"), aad.encode("utf-8"))
    return encrypted, nonce, fingerprint_contact_value(contact_type, normalized), mask_contact_value(contact_type, normalized)


def decrypt_contact_value(encrypted: bytes, nonce: bytes, *, aad: str) -> str:
    cipher = AESGCM(_key())
    plaintext = cipher.decrypt(nonce, encrypted, aad.encode("utf-8"))
    return plaintext.decode("utf-8")
