from __future__ import annotations
from dataclasses import dataclass
from enum import Enum


class LeadRoute(str, Enum):
    TRUCK = "TRUCK"
    NON_TRUCK_PI = "NON_TRUCK_PI"
    REJECT = "REJECT"


class AlertLevel(str, Enum):
    CRITICAL = "CRITICAL"
    WARN = "WARN"
    INFO = "INFO"


@dataclass(frozen=True)
class ExplainRow:
    feature: str
    contribution: float
    reason: str


@dataclass(frozen=True)
class Alert:
    level: AlertLevel
    message: str


@dataclass(frozen=True)
class ComplianceTrace:
    sources: list[str]
    filters_applied: list[str]
    notes: list[str]
