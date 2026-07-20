from __future__ import annotations
from typing import Protocol


class LeadRepository(Protocol):
    def save(self, lead_id: str, payload: dict) -> None: ...
    def get(self, lead_id: str) -> dict | None: ...


class InMemoryLeadRepository:
    def __init__(self):
        self._items: dict[str, dict] = {}

    def save(self, lead_id: str, payload: dict) -> None:
        self._items[lead_id] = dict(payload)

    def get(self, lead_id: str) -> dict | None:
        item = self._items.get(lead_id)
        return dict(item) if item else None
