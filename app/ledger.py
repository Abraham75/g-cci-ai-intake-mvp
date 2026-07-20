from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from threading import RLock
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


class LedgerEntry(BaseModel):
    entry_id: str = Field(default_factory=lambda: str(uuid4()))
    aggregate_type: str
    aggregate_id: str
    event_type: str
    payload: dict[str, Any]
    actor: str
    occurred_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    previous_hash: str = "GENESIS"
    entry_hash: str


_LOCK = RLock()
_ENTRIES: list[LedgerEntry] = []


def _canonical_payload(data: dict[str, Any]) -> str:
    return json.dumps(data, sort_keys=True, separators=(",", ":"), default=str)


def _hash_entry(*, aggregate_type: str, aggregate_id: str, event_type: str,
                payload: dict[str, Any], actor: str, occurred_at: datetime,
                previous_hash: str) -> str:
    material = "|".join([
        previous_hash,
        aggregate_type,
        aggregate_id,
        event_type,
        actor,
        occurred_at.isoformat(),
        _canonical_payload(payload),
    ])
    return hashlib.sha256(material.encode("utf-8")).hexdigest()


def append_entry(*, aggregate_type: str, aggregate_id: str, event_type: str,
                 payload: dict[str, Any], actor: str = "system") -> LedgerEntry:
    """Append-only decision ledger.

    Entries are hash-chained. Existing entries are never updated or deleted.
    This is an MVP in-memory implementation; production should persist the same
    contract in append-only durable storage.
    """
    with _LOCK:
        occurred_at = datetime.now(timezone.utc)
        previous_hash = _ENTRIES[-1].entry_hash if _ENTRIES else "GENESIS"
        entry_hash = _hash_entry(
            aggregate_type=aggregate_type,
            aggregate_id=aggregate_id,
            event_type=event_type,
            payload=payload,
            actor=actor,
            occurred_at=occurred_at,
            previous_hash=previous_hash,
        )
        entry = LedgerEntry(
            aggregate_type=aggregate_type,
            aggregate_id=aggregate_id,
            event_type=event_type,
            payload=payload,
            actor=actor,
            occurred_at=occurred_at,
            previous_hash=previous_hash,
            entry_hash=entry_hash,
        )
        _ENTRIES.append(entry)
        return entry


def list_entries(*, aggregate_type: str | None = None,
                 aggregate_id: str | None = None) -> list[LedgerEntry]:
    with _LOCK:
        result = list(_ENTRIES)
    if aggregate_type is not None:
        result = [e for e in result if e.aggregate_type == aggregate_type]
    if aggregate_id is not None:
        result = [e for e in result if e.aggregate_id == aggregate_id]
    return result


def query_current_state(*, aggregate_type: str, aggregate_id: str) -> dict[str, Any]:
    """Reduce ledger events into the current overlay state for one aggregate."""
    state: dict[str, Any] = {}
    for entry in list_entries(aggregate_type=aggregate_type, aggregate_id=aggregate_id):
        state.update(entry.payload)
        state["_last_event_type"] = entry.event_type
        state["_last_entry_hash"] = entry.entry_hash
        state["_last_occurred_at"] = entry.occurred_at.isoformat()
    return state


def verify_chain() -> bool:
    with _LOCK:
        entries = list(_ENTRIES)
    previous = "GENESIS"
    for entry in entries:
        expected = _hash_entry(
            aggregate_type=entry.aggregate_type,
            aggregate_id=entry.aggregate_id,
            event_type=entry.event_type,
            payload=entry.payload,
            actor=entry.actor,
            occurred_at=entry.occurred_at,
            previous_hash=previous,
        )
        if entry.previous_hash != previous or entry.entry_hash != expected:
            return False
        previous = entry.entry_hash
    return True
