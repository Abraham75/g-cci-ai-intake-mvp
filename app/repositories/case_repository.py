from __future__ import annotations
from typing import Protocol


class CaseRepository(Protocol):
    def save(self, case_file_id: str, payload: dict) -> None: ...
    def get(self, case_file_id: str) -> dict | None: ...


class InMemoryCaseRepository:
    def __init__(self):
        self._items: dict[str, dict] = {}

    def save(self, case_file_id: str, payload: dict) -> None:
        self._items[case_file_id] = dict(payload)

    def get(self, case_file_id: str) -> dict | None:
        item = self._items.get(case_file_id)
        return dict(item) if item else None
