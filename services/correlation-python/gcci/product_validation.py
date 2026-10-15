from __future__ import annotations

from dataclasses import dataclass


POSITIVE_DISPOSITIONS = {"GOOD_CASE"}
INVESTIGATED_STAGES = {"INVESTIGATED", "ADVANCED", "SIGNED", "REFERRED", "SETTLED"}
ADVANCED_STAGES = {"ADVANCED", "SIGNED", "REFERRED", "SETTLED"}


@dataclass(frozen=True)
class RankedLabel:
    hypothesis_id: str
    score: float
    attorney_worthy: bool | None


def precision_at_k(rows: list[RankedLabel], k: int) -> float | None:
    if k <= 0:
        raise ValueError("k must be positive")
    reviewed = [row for row in sorted(rows, key=lambda row: row.score, reverse=True)[:k]
                if row.attorney_worthy is not None]
    if not reviewed:
        return None
    return sum(1 for row in reviewed if row.attorney_worthy) / len(reviewed)


def qualification_precision(rows: list[RankedLabel]) -> float | None:
    reviewed = [row for row in rows if row.attorney_worthy is not None]
    if not reviewed:
        return None
    return sum(1 for row in reviewed if row.attorney_worthy) / len(reviewed)


def investigation_yield(outcome_stages: list[str]) -> float | None:
    investigated = [stage for stage in outcome_stages if stage in INVESTIGATED_STAGES]
    if not investigated:
        return None
    advanced = sum(1 for stage in investigated if stage in ADVANCED_STAGES)
    return advanced / len(investigated)
