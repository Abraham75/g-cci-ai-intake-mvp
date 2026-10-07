from __future__ import annotations

from dataclasses import dataclass

from .config import Settings, settings
from .models import CameraCandidate, EvidenceGap, IncidentHypothesis, NormalizedEvent


@dataclass(frozen=True)
class GapRule:
    evidence_type: str
    question: str
    probability_exists: float
    probability_resolves: float
    materiality: float
    preservation_urgency: float
    recommended_action: str


BASE_RULES = [
    GapRule("CCTV", "Can video establish vehicle identity, sequence, trajectory, or mechanism?", 0.70, 0.85, 0.95, 0.95, "Preserve and acquire the highest-relevance roadway-camera footage immediately."),
    GapRule("CAD_911", "Do CAD/911 timestamps and narratives corroborate event sequence and location?", 0.90, 0.65, 0.75, 0.60, "Request CAD event detail, call timestamps, and available call-audio metadata."),
    GapRule("CRASH_REPORT", "Does the official crash narrative identify parties, citations, injuries, or contributing factors?", 0.90, 0.75, 0.85, 0.45, "Acquire the full crash report, narrative, diagram, and supplements."),
    GapRule("TOW_RECORD", "Can towing/recovery records identify involved vehicles or preserve condition evidence?", 0.60, 0.70, 0.70, 0.70, "Identify the responding tow/recovery provider and preserve dispatch/invoice records."),
    GapRule("EDR", "Can vehicle event data establish speed, braking, or impact dynamics?", 0.45, 0.90, 0.90, 0.85, "If a vehicle is identified, preserve EDR/ECM data before overwrite or disposal."),
    GapRule("ELD_TELEMATICS", "Can commercial telematics establish vehicle presence, route, hours, or driver behavior?", 0.55, 0.85, 0.90, 0.90, "If CMV involvement is corroborated, preserve ELD/GPS/telematics."),
    GapRule("FMCSA_CARRIER", "Can carrier records establish the commercial defendant and relevant safety context?", 0.75, 0.70, 0.80, 0.35, "After a carrier identifier is lawfully resolved, enrich with FMCSA carrier/safety records."),
]


def rank_evidence_gaps(
    hypothesis: IncidentHypothesis,
    events: list[NormalizedEvent],
    nearest_cameras: list[CameraCandidate],
    cfg: Settings = settings,
) -> list[EvidenceGap]:
    source_kinds = {e.source_kind.value for e in events}
    has_camera = bool(nearest_cameras)
    commercial = any(e.commercial_vehicle_hint for e in events)
    injury = any(e.injury_hint or e.fatality_hint for e in events)
    wheel_or_debris = any(e.wheel_off_hint or e.debris_hint for e in events)

    out: list[EvidenceGap] = []
    for rule in BASE_RULES:
        if rule.evidence_type == "CCTV" and "CAMERA" in source_kinds:
            continue
        if rule.evidence_type == "CAD_911" and "CAD" in source_kinds:
            continue
        if rule.evidence_type == "CRASH_REPORT" and "CRASH_REPORT" in source_kinds:
            continue

        p_exists = rule.probability_exists
        p_resolves = rule.probability_resolves
        materiality = rule.materiality
        urgency = rule.preservation_urgency

        if rule.evidence_type == "CCTV":
            p_exists = 0.95 if has_camera else p_exists
            urgency = 1.0 if has_camera else urgency
        if rule.evidence_type in {"ELD_TELEMATICS", "FMCSA_CARRIER"} and commercial:
            p_exists = min(1.0, p_exists + 0.20)
            materiality = min(1.0, materiality + 0.05)
        if rule.evidence_type == "EDR" and injury:
            materiality = min(1.0, materiality + 0.05)
        if rule.evidence_type in {"CCTV", "TOW_RECORD"} and wheel_or_debris:
            p_resolves = min(1.0, p_resolves + 0.10)

        gain = p_exists * p_resolves * materiality * urgency
        out.append(
            EvidenceGap(
                evidence_type=rule.evidence_type,
                question=rule.question,
                probability_exists=round(p_exists, 4),
                probability_resolves=round(p_resolves, 4),
                materiality=round(materiality, 4),
                preservation_urgency=round(urgency, 4),
                expected_information_gain=round(gain, 4),
                recommended_action=rule.recommended_action,
            )
        )

    out.sort(key=lambda x: x.expected_information_gain, reverse=True)
    return out[: cfg.max_gap_results]
