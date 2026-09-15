from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional
from pydantic import BaseModel, Field


class SourceKind(str, Enum):
    GDOT_511 = "GDOT_511"
    GDOT_ARCGIS = "GDOT_ARCGIS"
    GEMA_WAZE = "GEMA_WAZE"
    WAZE_PARTNER = "WAZE_PARTNER"
    CAMERA = "CAMERA"
    CRASH_REPORT = "CRASH_REPORT"
    CAD = "CAD"
    OTHER = "OTHER"


class CorrelationClass(str, Enum):
    SAME_INCIDENT = "same_incident"
    RELATED_INCIDENT = "related_incident"
    POSSIBLE_CONNECTION = "possible_connection"
    UNRELATED = "unrelated"


class HypothesisStatus(str, Enum):
    MACHINE_PROPOSED = "MachineProposed"
    ANALYST_CONFIRMED = "AnalystConfirmed"
    ANALYST_REJECTED = "AnalystRejected"
    NEEDS_MORE_EVIDENCE = "NeedsMoreEvidence"


class GeoPoint(BaseModel):
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)


class Provenance(BaseModel):
    source_system: str
    source_record_id: str
    source_url: Optional[str] = None
    retrieved_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    raw_sha256: Optional[str] = None


class NormalizedEvent(BaseModel):
    id: str
    source_kind: SourceKind
    observed_at: datetime
    reported_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    point: Optional[GeoPoint] = None
    roadway: Optional[str] = None
    direction: Optional[str] = None
    location_text: Optional[str] = None
    event_type: str
    description: str = ""
    lanes_affected: Optional[str] = None
    commercial_vehicle_hint: bool = False
    injury_hint: bool = False
    fatality_hint: bool = False
    closure_hint: bool = False
    stalled_vehicle_hint: bool = False
    debris_hint: bool = False
    wheel_off_hint: bool = False
    attributes: dict[str, str] = Field(default_factory=dict)
    provenance: Provenance
    raw: dict[str, Any] = Field(default_factory=dict)


class Camera(BaseModel):
    id: str
    name: str
    point: GeoPoint
    roadway: Optional[str] = None
    direction: Optional[str] = None
    snapshot_url: Optional[str] = None
    stream_url: Optional[str] = None
    source_system: str = "GDOT_CAMERA"
    provenance: Optional[Provenance] = None


class FactorScore(BaseModel):
    factor: str
    score: float = Field(ge=0, le=1)
    reason: str


class PairCorrelation(BaseModel):
    event_a_id: str
    event_b_id: str
    score: float = Field(ge=0, le=1)
    classification: CorrelationClass
    factors: list[FactorScore]
    contradictions: list[str] = Field(default_factory=list)


class IncidentHypothesis(BaseModel):
    id: str
    member_event_ids: list[str]
    machine_confidence: float = Field(ge=0, le=1)
    classification: CorrelationClass
    rationale: list[str]
    contradictions: list[str] = Field(default_factory=list)
    centroid: Optional[GeoPoint] = None
    start_time: datetime
    end_time: datetime
    roadway: Optional[str] = None
    direction: Optional[str] = None
    status: HypothesisStatus = HypothesisStatus.MACHINE_PROPOSED
    analyst_note: Optional[str] = None
    model_version: str = "gcci-cross-source-correlation-v1.0.0"


class CameraCandidate(BaseModel):
    camera: Camera
    distance_meters: float
    roadway_match: bool
    direction_match: bool
    relevance_score: float = Field(ge=0, le=1)


class EvidenceGap(BaseModel):
    evidence_type: str
    question: str
    probability_exists: float = Field(ge=0, le=1)
    probability_resolves: float = Field(ge=0, le=1)
    materiality: float = Field(ge=0, le=1)
    preservation_urgency: float = Field(ge=0, le=1)
    expected_information_gain: float = Field(ge=0, le=1)
    recommended_action: str


class CorrelatedIncidentPackage(BaseModel):
    hypothesis: IncidentHypothesis
    events: list[NormalizedEvent]
    pairwise_correlations: list[PairCorrelation]
    nearest_cameras: list[CameraCandidate]
    evidence_gaps: list[EvidenceGap]
    causal_relationship_confidence: Optional[float] = None
    party_attribution_confidence: Optional[float] = None
    contact_eligibility: str = "NOT_EVALUATED"
