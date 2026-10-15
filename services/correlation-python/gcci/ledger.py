from __future__ import annotations

import hashlib
import json
from typing import Any
from uuid import uuid4

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from .database import DecisionLedgerRow


LEDGER_LOCK_KEY = 874221


def _canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)


def _entry_hash(
    *,
    entry_id: str,
    entry_type: str,
    subject_id: str,
    payload: dict[str, Any],
    produced_by: str,
    source_system: str | None,
    model_version: str | None,
    input_entry_ids: list[str],
    supersedes_entry_id: str | None,
    previous_hash: str | None,
) -> str:
    material = {
        "id": entry_id,
        "entry_type": entry_type,
        "subject_id": subject_id,
        "payload": payload,
        "produced_by": produced_by,
        "source_system": source_system,
        "model_version": model_version,
        "input_entry_ids": input_entry_ids,
        "supersedes_entry_id": supersedes_entry_id,
        "previous_hash": previous_hash,
    }
    return hashlib.sha256(_canonical_json(material).encode("utf-8")).hexdigest()


async def append_ledger_entry(
    session: AsyncSession,
    *,
    entry_type: str,
    subject_id: str,
    payload: dict[str, Any],
    produced_by: str,
    source_system: str | None = None,
    model_version: str | None = None,
    input_entry_ids: list[str] | None = None,
    supersedes_entry_id: str | None = None,
) -> DecisionLedgerRow:
    """Append one immutable ledger row under a transaction-scoped advisory lock.

    The advisory lock serializes the global SHA-256 chain across multiple API and
    worker processes. The caller owns the database transaction; rollback removes
    both the business mutation and its ledger append atomically.
    """
    await session.execute(text("SELECT pg_advisory_xact_lock(:key)"), {"key": LEDGER_LOCK_KEY})

    previous = (
        await session.execute(
            select(DecisionLedgerRow).order_by(DecisionLedgerRow.sequence_no.desc()).limit(1)
        )
    ).scalar_one_or_none()

    entry_id = str(uuid4())
    input_ids = input_entry_ids or []
    previous_hash = previous.entry_hash if previous else None
    digest = _entry_hash(
        entry_id=entry_id,
        entry_type=entry_type,
        subject_id=subject_id,
        payload=payload,
        produced_by=produced_by,
        source_system=source_system,
        model_version=model_version,
        input_entry_ids=input_ids,
        supersedes_entry_id=supersedes_entry_id,
        previous_hash=previous_hash,
    )

    row = DecisionLedgerRow(
        id=entry_id,
        entry_type=entry_type,
        subject_id=subject_id,
        payload_json=payload,
        produced_by=produced_by,
        source_system=source_system,
        model_version=model_version,
        input_entry_ids_json=input_ids,
        supersedes_entry_id=supersedes_entry_id,
        previous_hash=previous_hash,
        entry_hash=digest,
    )
    session.add(row)
    await session.flush()
    return row


async def ledger_entries_for_subject(
    session: AsyncSession, subject_id: str
) -> list[DecisionLedgerRow]:
    rows = (
        await session.execute(
            select(DecisionLedgerRow)
            .where(DecisionLedgerRow.subject_id == subject_id)
            .order_by(DecisionLedgerRow.sequence_no)
        )
    ).scalars().all()
    return list(rows)


async def verify_ledger_chain(session: AsyncSession) -> tuple[bool, str | None]:
    rows = (
        await session.execute(select(DecisionLedgerRow).order_by(DecisionLedgerRow.sequence_no))
    ).scalars().all()

    previous_hash: str | None = None
    for row in rows:
        if row.previous_hash != previous_hash:
            return False, f"Broken previous_hash at sequence {row.sequence_no}"

        expected = _entry_hash(
            entry_id=row.id,
            entry_type=row.entry_type,
            subject_id=row.subject_id,
            payload=row.payload_json,
            produced_by=row.produced_by,
            source_system=row.source_system,
            model_version=row.model_version,
            input_entry_ids=row.input_entry_ids_json,
            supersedes_entry_id=row.supersedes_entry_id,
            previous_hash=row.previous_hash,
        )
        if expected != row.entry_hash:
            return False, f"Hash mismatch at sequence {row.sequence_no}"
        previous_hash = row.entry_hash

    return True, None
