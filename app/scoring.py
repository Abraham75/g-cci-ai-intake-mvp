from __future__ import annotations

from enum import Enum


class IncidentMechanism(str, Enum):
    REAR_END = "RearEndCollision"
    ANGLE = "AngleCollision"
    SIDESWIPE = "SideswipeCollision"
    DEBRIS = "DebrisIncident"
    WHEEL_OFF = "WheelOffIncident"
    MECHANICAL_FAILURE = "MechanicalFailureIncident"
    VEHICLE_STALL = "VehicleStall"


MECHANISM_DISPLAY_LABEL: dict[IncidentMechanism, str] = {
    IncidentMechanism.REAR_END: "Rear-End Collision",
    IncidentMechanism.ANGLE: "Angle Collision",
    IncidentMechanism.SIDESWIPE: "Sideswipe Collision",
    IncidentMechanism.DEBRIS: "Debris Incident",
    IncidentMechanism.WHEEL_OFF: "Wheel-Off Incident",
    IncidentMechanism.MECHANICAL_FAILURE: "Mechanical Failure",
    IncidentMechanism.VEHICLE_STALL: "Vehicle Stall",
}

MECHANISM_SEVERITY: dict[IncidentMechanism, float] = {
    IncidentMechanism.WHEEL_OFF: 0.90,
    IncidentMechanism.MECHANICAL_FAILURE: 0.75,
    IncidentMechanism.ANGLE: 0.65,
    IncidentMechanism.SIDESWIPE: 0.60,
    IncidentMechanism.DEBRIS: 0.55,
    IncidentMechanism.REAR_END: 0.50,
    IncidentMechanism.VEHICLE_STALL: 0.30,
}


def compute_case_opportunity_score(
    liability: float,
    injury: float,
    collectability: float,
    evidence: float,
    mechanism_severity: float,
    defendant_resolution: float,
    uncertainty_penalty: float,
) -> float:
    """Canonical G-CCI Case Opportunity Score.

    COS = .25L + .20I + .20C + .15E + .10M + .10D - .20U
    """
    raw = (
        0.25 * liability
        + 0.20 * injury
        + 0.20 * collectability
        + 0.15 * evidence
        + 0.10 * mechanism_severity
        + 0.10 * defendant_resolution
        - 0.20 * uncertainty_penalty
    )
    return max(0.0, min(1.0, raw))


def classify_tier(cos: float, has_unresolved_high_severity_contradiction: bool) -> str:
    if has_unresolved_high_severity_contradiction:
        return "C"
    if cos >= 0.80:
        return "A"
    if cos >= 0.65:
        return "B"
    if cos >= 0.45:
        return "C"
    return "D"


def compute_uncertainty_penalty(num_high_severity_unresolved: int, num_other: int = 0) -> float:
    return min(1.0, round(0.22 * num_high_severity_unresolved + 0.05 * num_other, 2))


def compute_event_correlation(evidence_count: int) -> float:
    return round(min(1.0, 0.5 + 0.25 * evidence_count), 2)


def compute_causal_relationship(event_correlation: float, has_any_contradiction: bool) -> float:
    return round(event_correlation * (0.9 if not has_any_contradiction else 0.6), 2)


def compute_party_attribution(num_parties: int, num_resolved: int) -> float:
    return round(0.5 * (num_resolved / num_parties), 2) if num_parties else 0.0


EXPECTED_EVIDENCE_TYPES = ["Crash Report", "CCTV", "CAD Record", "Tow Record", "EDR", "ELD"]
