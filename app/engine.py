"""G-CCI scoring engine.

This module preserves the original intake routing helpers while delegating the
canonical Case Opportunity Score and confidence math to app.scoring. This
removes the divergent scoring implementation that previously existed between
engine.py, the backend prototype, and the React frontend.
"""

import math
from dataclasses import dataclass

from app.scoring import (
    MECHANISM_SEVERITY,
    IncidentMechanism,
    classify_tier,
    compute_case_opportunity_score,
    compute_causal_relationship,
    compute_event_correlation,
    compute_party_attribution,
    compute_uncertainty_penalty,
)

TRUCK_TYPES = {
    "18-wheeler", "tractor-trailer", "commercial truck", "box truck", "bus/fleet"
}

SEVERITY_WEIGHT = {"moderate": 0.5, "high": 0.8, "catastrophic": 1.0}

DEFENDANT_BONUS = {
    "National Carrier": 18,
    "Mega Carrier": 22,
    "Fortune 500": 20,
    "Regional Fleet": 10,
    "Individual/Small Biz": 4,
}

COUNTY_BONUS = {
    "Cobb": 10, "Spalding": 8, "Lowndes": 8,
    "Fulton": 7, "DeKalb": 6, "Gwinnett": 5, "Clayton": 4,
}


def route_submodel(incident_type: str) -> str:
    return "TRUCK_SUBMODEL" if incident_type in TRUCK_TYPES else "NON_TRUCK_SUBMODEL"


def _sigmoid(x: float) -> float:
    return 1 / (1 + math.exp(-x))


def score_truck(intake):
    """Legacy intake score retained for backward compatibility."""
    base = 55
    base += int(30 * SEVERITY_WEIGHT[intake.severity])
    base += DEFENDANT_BONUS.get(intake.defendant_type, 6)
    base += COUNTY_BONUS.get(intake.county, 3)
    if intake.hours_of_service_flag:
        base += 10
    if intake.fmcsa_signal:
        base += 8
    if intake.police_report_available:
        base += 4
    lead_score = min(99, base)
    conf_raw = 0.9 * SEVERITY_WEIGHT[intake.severity] + 0.3 * (DEFENDANT_BONUS.get(intake.defendant_type, 6) / 22)
    confidence = int(99 * _sigmoid((conf_raw - 0.7) * 4))
    if lead_score >= 90:
        value = "$2.5M – $5M+"
    elif lead_score >= 80:
        value = "$1.0M – $2.5M"
    elif lead_score >= 65:
        value = "$350K – $1.0M"
    else:
        value = "$150K – $350K"
    return lead_score, confidence, value


def score_non_truck(intake):
    """Legacy intake score retained for backward compatibility."""
    base = 40
    base += int(25 * SEVERITY_WEIGHT[intake.severity])
    base += COUNTY_BONUS.get(intake.county, 2)
    if intake.incident_type in ("motorcycle", "pedestrian", "bicycle"):
        base += 10
    lead_score = min(89, base)
    confidence = int(99 * _sigmoid((SEVERITY_WEIGHT[intake.severity] - 0.6) * 4))
    if lead_score >= 80:
        value = "$600K – $1.2M"
    elif lead_score >= 65:
        value = "$250K – $600K"
    else:
        value = "$50K – $250K"
    return lead_score, confidence, value


@dataclass(frozen=True)
class OpportunityInput:
    mechanism: IncidentMechanism
    liability: float
    injury: float
    collectability: float
    evidence: float
    defendant_resolution: float
    unresolved_high_contradictions: int = 0
    other_contradictions: int = 0
    evidence_count: int = 0
    party_count: int = 0
    resolved_party_count: int = 0


def score_case_opportunity(data: OpportunityInput) -> dict:
    """Canonical attorney-facing opportunity score and independent confidences."""
    uncertainty = compute_uncertainty_penalty(
        data.unresolved_high_contradictions, data.other_contradictions
    )
    mechanism_severity = MECHANISM_SEVERITY[data.mechanism]
    cos = compute_case_opportunity_score(
        data.liability,
        data.injury,
        data.collectability,
        data.evidence,
        mechanism_severity,
        data.defendant_resolution,
        uncertainty,
    )
    event_correlation = compute_event_correlation(data.evidence_count)
    causal_relationship = compute_causal_relationship(
        event_correlation,
        (data.unresolved_high_contradictions + data.other_contradictions) > 0,
    )
    party_attribution = compute_party_attribution(
        data.party_count, data.resolved_party_count
    )
    return {
        "cos": round(cos, 2),
        "tier": classify_tier(cos, data.unresolved_high_contradictions > 0),
        "scores": {
            "liability": data.liability,
            "injury": data.injury,
            "collectability": data.collectability,
            "evidence": data.evidence,
            "mechanismSeverity": mechanism_severity,
            "defendantResolution": data.defendant_resolution,
            "uncertaintyPenalty": uncertainty,
        },
        "confidence": {
            "eventCorrelation": event_correlation,
            "causalRelationship": causal_relationship,
            "partyAttribution": party_attribution,
        },
    }
