from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from app.engine import OpportunityInput, score_case_opportunity
from app.ledger import append_entry, list_entries, query_current_state, verify_chain
from app.scoring import EXPECTED_EVIDENCE_TYPES, IncidentMechanism, MECHANISM_DISPLAY_LABEL

app = FastAPI(title="G-CCI Consolidated Backend", version="1.1.0-demo")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class FactStatus(str, Enum):
    OBSERVED = "Observed Fact"
    INFERRED = "Inferred Fact"
    ALLEGATION = "Allegation"
    MODEL_PREDICTION = "Model Prediction"
    ATTORNEY_VALIDATED = "Attorney Validated Fact"


class PartyRole(str, Enum):
    DRIVER = "Driver"
    REGISTERED_OWNER = "Registered Owner"
    MOTOR_CARRIER = "Motor Carrier"
    WITNESS = "Witness"
    INJURED_PARTY = "Injured Party"


class PartyStage(str, Enum):
    UNKNOWN = "UNKNOWN"
    CANDIDATE = "CANDIDATE"
    CORROBORATED = "CORROBORATED"
    VERIFIED = "VERIFIED"


class LegalAccessBasis(str, Enum):
    NOT_ESTABLISHED = "NotEstablished"
    PUBLIC_RECORD = "PublicRecord"
    OPEN_RECORDS_REQUEST = "OpenRecordsRequest"
    CLIENT_PROVIDED = "ClientProvided"


class SolicitationReviewStatus(str, Enum):
    NOT_REVIEWED = "NotReviewed"
    WITHIN_HOLD_PERIOD = "WithinHoldPeriod"
    CLEARED_BY_COUNSEL = "ClearedByCounsel"
    REJECTED_BY_COUNSEL = "RejectedByCounsel"


class AssertionStatus(str, Enum):
    MACHINE_PROPOSED = "MachineProposed"
    ANALYST_CONFIRMED = "AnalystConfirmed"
    ANALYST_REJECTED = "AnalystRejected"
    NEEDS_MORE_EVIDENCE = "NeedsMoreEvidence"


class HypothesisType(str, Enum):
    INDEPENDENT_EVENTS = "IndependentEventsHypothesis"
    SEQUENTIAL_CAUSATION = "SequentialCausationHypothesis"
    VEHICLE_FAILURE = "VehicleFailureHypothesis"
    DEBRIS_CAUSATION = "DebrisCausationHypothesis"


class Location(BaseModel):
    roadSegment: str
    mileMarker: Optional[float] = None

    @property
    def display(self) -> str:
        return f"{self.roadSegment} @ MM {self.mileMarker}" if self.mileMarker is not None else self.roadSegment


class EvidenceItem(BaseModel):
    id: str
    type: str
    source: str
    timestamp: datetime
    factStatus: str = FactStatus.OBSERVED.value
    provenance: str
    attributes: Optional[dict[str, str]] = None


class HypothesisItem(BaseModel):
    id: str
    description: str
    type: HypothesisType
    confidence: float
    supporting: list[str] = Field(default_factory=list)
    contradicting: list[str] = Field(default_factory=list)
    status: AssertionStatus = AssertionStatus.MACHINE_PROPOSED
    analystDecision: Optional[str] = None
    analystNote: Optional[str] = None


class ContradictionItem(BaseModel):
    id: str
    type: str
    assertionA: str
    assertionB: str
    severity: str
    impactOnScore: float
    resolved: bool = False


class PartyItem(BaseModel):
    id: str
    role: PartyRole
    stage: PartyStage
    note: str
    legalAccessBasis: LegalAccessBasis = LegalAccessBasis.NOT_ESTABLISHED
    solicitationReview: SolicitationReviewStatus = SolicitationReviewStatus.NOT_REVIEWED
    suppressionChecked: bool = False


class BaseScores(BaseModel):
    liability: float
    injury: float
    collectability: float
    evidence: float
    defendantResolution: float


class Incident(BaseModel):
    id: str
    label: str
    mechanism: IncidentMechanism
    occurredAt: datetime
    location: Location
    carrierDesc: Optional[str] = None
    isCMV: bool
    vehicleTypes: list[str] = Field(default_factory=list)
    liabilitySignals: list[str] = Field(default_factory=list)
    injurySignals: list[str] = Field(default_factory=list)
    evidence: list[EvidenceItem] = Field(default_factory=list)
    hypotheses: list[HypothesisItem] = Field(default_factory=list)
    contradictions: list[ContradictionItem] = Field(default_factory=list)
    parties: list[PartyItem] = Field(default_factory=list)
    baseScores: BaseScores


def _hypothesis_with_ledger(h: HypothesisItem) -> HypothesisItem:
    state = query_current_state(aggregate_type="hypothesis", aggregate_id=h.id)
    if not state:
        return h
    return h.model_copy(update={
        "status": state.get("status", h.status),
        "analystDecision": state.get("analystDecision", h.analystDecision),
        "analystNote": state.get("analystNote", h.analystNote),
    })


def _party_with_ledger(p: PartyItem) -> PartyItem:
    state = query_current_state(aggregate_type="party", aggregate_id=p.id)
    if not state:
        return p
    return p.model_copy(update={
        "legalAccessBasis": state.get("legalAccessBasis", p.legalAccessBasis),
        "solicitationReview": state.get("solicitationReview", p.solicitationReview),
        "suppressionChecked": state.get("suppressionChecked", p.suppressionChecked),
    })


def _incident_view(i: Incident) -> Incident:
    return i.model_copy(update={
        "hypotheses": [_hypothesis_with_ledger(h) for h in i.hypotheses],
        "parties": [_party_with_ledger(p) for p in i.parties],
    })


def _enrich(i: Incident) -> dict:
    i = _incident_view(i)
    high = sum(1 for c in i.contradictions if c.severity == "high" and not c.resolved)
    other = sum(1 for c in i.contradictions if not (c.severity == "high" and not c.resolved))
    result = score_case_opportunity(OpportunityInput(
        mechanism=i.mechanism,
        liability=i.baseScores.liability,
        injury=i.baseScores.injury,
        collectability=i.baseScores.collectability,
        evidence=i.baseScores.evidence,
        defendant_resolution=i.baseScores.defendantResolution,
        unresolved_high_contradictions=high,
        other_contradictions=other,
        evidence_count=len(i.evidence),
        party_count=len(i.parties),
        resolved_party_count=sum(1 for p in i.parties if p.stage == PartyStage.VERIFIED),
    ))
    present = {e.type for e in i.evidence}
    completeness = round(sum(1 for t in EXPECTED_EVIDENCE_TYPES if t in present) / len(EXPECTED_EVIDENCE_TYPES) * 100)
    return {
        "id": i.id,
        "label": i.label,
        "type": MECHANISM_DISPLAY_LABEL[i.mechanism],
        "occurredAt": i.occurredAt,
        "location": i.location.display,
        "isCMV": i.isCMV,
        "vehicleTypes": i.vehicleTypes,
        "liabilitySignals": i.liabilitySignals,
        "injurySignals": i.injurySignals,
        "evidence": [e.model_dump() for e in i.evidence],
        "hypotheses": [h.model_dump() for h in i.hypotheses],
        "contradictions": [c.model_dump() for c in i.contradictions],
        "parties": [p.model_dump() for p in i.parties],
        "scores": result["scores"],
        "confidence": result["confidence"],
        "cos": result["cos"],
        "tier": result["tier"],
        "completeness": completeness,
    }


def ev(eid: str, typ: str, source: str, ts: datetime, provenance: str, **kwargs) -> EvidenceItem:
    return EvidenceItem(id=eid, type=typ, source=source, timestamp=ts, provenance=provenance, **kwargs)


def incident(iid: str, label: str, mechanism: IncidentMechanism, dt: datetime, road: str, mm: float,
             is_cmv: bool, vehicles: list[str], liability: float, injury: float,
             collectability: float, evidence_score: float, defendant_resolution: float,
             liability_signals: list[str] | None = None, injury_signals: list[str] | None = None,
             evidence: list[EvidenceItem] | None = None, hypotheses: list[HypothesisItem] | None = None,
             contradictions: list[ContradictionItem] | None = None, parties: list[PartyItem] | None = None,
             carrier: str | None = None) -> Incident:
    return Incident(
        id=iid, label=label, mechanism=mechanism, occurredAt=dt,
        location=Location(roadSegment=road, mileMarker=mm), carrierDesc=carrier,
        isCMV=is_cmv, vehicleTypes=vehicles, liabilitySignals=liability_signals or [],
        injurySignals=injury_signals or [], evidence=evidence or [], hypotheses=hypotheses or [],
        contradictions=contradictions or [], parties=parties or [],
        baseScores=BaseScores(liability=liability, injury=injury, collectability=collectability,
                              evidence=evidence_score, defendantResolution=defendant_resolution),
    )


SEED = [
    incident(
        "PhillipsIncident", "Phillips Incident", IncidentMechanism.SIDESWIPE,
        datetime(2025, 12, 9, 14, 20), "I-285 WB", 24.5, False, ["Passenger SUV"],
        .4, .5, .2, .35, .15, ["MechanicalFailure"], ["ReportedInjury", "EMSResponse"],
        evidence=[ev("ev_001", "Crash Report", "DEMO_GDOT", datetime(2025,12,9,14,25), "Open Records Request (synthetic)")],
        hypotheses=[
            HypothesisItem(id="hyp_p1", description="SUV struck by debris originating from Event5122820.", type=HypothesisType.SEQUENTIAL_CAUSATION, confidence=.74, supporting=["ev_001"]),
            HypothesisItem(id="hyp_p2", description="SUV struck by debris of unrelated, unidentified origin.", type=HypothesisType.INDEPENDENT_EVENTS, confidence=.21, contradicting=["ev_001"]),
        ],
        parties=[PartyItem(id="party_001", role=PartyRole.INJURED_PARTY, stage=PartyStage.CANDIDATE, note="Occupant of SUV struck by debris.")],
    ),
    incident(
        "Event5122820", "Event 5122820", IncidentMechanism.WHEEL_OFF,
        datetime(2025,12,9,13,53), "I-285 WB", 24.8, True, ["Unidentified Work Truck"],
        .6, 0, .5, .4, .15, ["MechanicalFailure", "ImproperMaintenance"],
        evidence=[
            ev("ev_002", "CCTV", "DEMO_GDOT_CCTV", datetime(2025,12,9,13,53), "Restricted Government Data (synthetic)", attributes={"vehicle_color":"white"}),
            ev("ev_003", "Witness Statement", "DEMO_witness", datetime(2025,12,9,13,55), "Discovery Obtainable (synthetic)", factStatus=FactStatus.ALLEGATION.value, attributes={"vehicle_color":"blue"}),
        ],
        hypotheses=[HypothesisItem(id="hyp_e1", description="Wheel separated from commercial work truck due to maintenance-related failure.", type=HypothesisType.VEHICLE_FAILURE, confidence=.58, supporting=["ev_002"], contradicting=["ev_003"])],
        contradictions=[ContradictionItem(id="con_001", type="vehicle_color_conflict", assertionA="ev_002: white", assertionB="ev_003: blue", severity="high", impactOnScore=-.22)],
        parties=[
            PartyItem(id="party_002", role=PartyRole.DRIVER, stage=PartyStage.UNKNOWN, note="Operator of unidentified work truck."),
            PartyItem(id="party_003", role=PartyRole.MOTOR_CARRIER, stage=PartyStage.CANDIDATE, note="Unverified carrier candidate."),
        ], carrier="Carrier X (demo, unverified)",
    ),
    incident("INC-10204758", "Tractor-Trailer / Passenger Vehicle", IncidentMechanism.ANGLE, datetime(2025,11,2,8,12), "I-75 SB",112.3,True,["Tractor-Trailer","Passenger Sedan"],.85,.75,.9,.8,.8,["ImproperLaneChange","FollowingTooClosely"],["ReportedInjury","EMSResponse","AirbagDeployment"], evidence=[ev("ev_101","Crash Report","DEMO_GDOT",datetime(2025,11,2,8,20),"Open Records Request (synthetic)"),ev("ev_102","CAD Record","DEMO_CAD",datetime(2025,11,2,8,14),"Public Record (synthetic)"),ev("ev_103","ELD","DEMO_Carrier",datetime(2025,11,2,7,50),"Discovery Obtainable (synthetic)")], parties=[PartyItem(id="party_101",role=PartyRole.MOTOR_CARRIER,stage=PartyStage.VERIFIED,note="Synthetic verified carrier.",legalAccessBasis=LegalAccessBasis.PUBLIC_RECORD,solicitationReview=SolicitationReviewStatus.CLEARED_BY_COUNSEL,suppressionChecked=True),PartyItem(id="party_102",role=PartyRole.INJURED_PARTY,stage=PartyStage.CORROBORATED,note="Synthetic injured party role.")]),
]

for args in [
    ("INC-10167438","Bobtail Lane-Change",IncidentMechanism.ANGLE,datetime(2025,10,14,16,40),"I-20 WB",5.0,True,["Bobtail Tractor"],.5,.1,.5,.4,.3),
    ("INC-10166139","Passenger Intersection Collision",IncidentMechanism.ANGLE,datetime(2025,9,20,16),"I-675 SB",5.0,False,["Passenger Sedan","Passenger Sedan"],.1,0,0,0,0),
    ("INC-10167485","Multi-Vehicle Sideswipe",IncidentMechanism.SIDESWIPE,datetime(2025,10,28,17,15),"I-85 NB",44.0,False,["Passenger SUV","Passenger Hatchback"],.45,.3,.1,.25,.2),
    ("INC-20391004","Work-Zone Debris Strike",IncidentMechanism.DEBRIS,datetime(2025,8,11,11,5),"I-16 EB",8.0,False,["Unknown"],.15,0,.1,.15,0),
    ("INC-20391088","Trailer Mechanical Failure",IncidentMechanism.MECHANICAL_FAILURE,datetime(2025,7,30,9,22),"I-575 NB",2.0,True,["Box Truck"],.55,0,.6,.3,.4),
    ("INC-20392201","Wheel-Off Secondary Event",IncidentMechanism.WHEEL_OFF,datetime(2025,6,5,12,10),"I-985 NB",1.0,True,["Tractor-Trailer"],.4,.15,.5,.2,.1),
    ("INC-20393310","Rear-End, Following Too Closely",IncidentMechanism.REAR_END,datetime(2025,9,10,7,45),"I-575 NB",2.0,False,["Passenger Sedan","Passenger Truck"],.5,.3,.15,.3,.25),
    ("INC-20394477","Vehicle Stall, Low Priority",IncidentMechanism.VEHICLE_STALL,datetime(2025,9,25,6,15),"I-985 NB",1.0,False,["Passenger Sedan"],.05,0,0,.1,0),
    ("INC-20395522","CMV Rear-End, Strong Signals",IncidentMechanism.REAR_END,datetime(2025,11,15,10),"I-20 WB",40.0,True,["Box Truck","Passenger Sedan"],.7,.6,.7,.5,.5),
    ("INC-20396633","Angle Collision, Evidence Pending",IncidentMechanism.ANGLE,datetime(2025,11,1,9),"I-20 WB",5.0,True,["Box Truck"],.4,0,.5,.15,.2),
    ("INC-20397744","Debris Incident, Unresolved",IncidentMechanism.DEBRIS,datetime(2025,12,9,14,10),"I-75 NB",10.0,False,["Unknown"],.1,0,0,.1,0),
    ("INC-20398855","Mechanical Failure, Coverage Pending",IncidentMechanism.MECHANICAL_FAILURE,datetime(2025,12,1,11),"I-75 SB",12.0,True,["Box Truck"],.5,0,.5,.3,.3),
]:
    SEED.append(incident(*args))

INCIDENTS = {i.id: i for i in SEED}
HYPOTHESIS_INDEX = {h.id: (i.id, h) for i in SEED for h in i.hypotheses}
PARTY_INDEX = {p.id: (i.id, p) for i in SEED for p in i.parties}


@app.get("/api/incidents")
def list_incidents():
    return [_enrich(i) for i in INCIDENTS.values()]


@app.get("/api/incidents/{incident_id}")
def get_incident(incident_id: str):
    if incident_id not in INCIDENTS:
        raise HTTPException(404, f"Unknown incident: {incident_id}")
    return _enrich(INCIDENTS[incident_id])


@app.get("/api/incidents/{incident_id}/explain")
def explain_incident(incident_id: str):
    if incident_id not in INCIDENTS:
        raise HTTPException(404, f"Unknown incident: {incident_id}")
    i = _incident_view(INCIDENTS[incident_id])
    e = _enrich(i)
    present = {ev.type for ev in i.evidence}
    missing = [t for t in EXPECTED_EVIDENCE_TYPES if t not in present]
    actions = [f"Obtain {m}" for m in missing[:3]]
    if any(c.severity == "high" and not c.resolved for c in i.contradictions):
        actions.append("Resolve unresolved contradiction before Tier A eligibility")
    if any(p.stage != PartyStage.VERIFIED for p in i.parties):
        actions.append("Continue party identity resolution")
    actions.append("Attorney review of compiled findings")
    return {
        "scoreNarrative": f"Case Opportunity Score {round(e['cos']*100)}; uncertainty penalty {round(e['scores']['uncertaintyPenalty']*100)} is computed from current contradiction evidence.",
        "supportingEvidence": [f"{ev.type} ({ev.source}) — {ev.factStatus}" for ev in i.evidence],
        "contradictoryEvidence": [f"{c.assertionA} vs. {c.assertionB} ({c.severity})" for c in i.contradictions],
        "missingEvidence": missing,
        "modelVersion": "gcci-cos-v1.1-consolidated-demo",
        "sourceProvenance": f"{len(i.evidence)} synthetic evidence item(s)",
        "recommendedActions": actions,
    }


class AnalystActionRequest(BaseModel):
    analystNote: Optional[str] = None


def _record_hypothesis_action(hypothesis_id: str, status: AssertionStatus, decision: str, note: str | None):
    if hypothesis_id not in HYPOTHESIS_INDEX:
        raise HTTPException(404, f"Unknown hypothesis: {hypothesis_id}")
    append_entry(
        aggregate_type="hypothesis",
        aggregate_id=hypothesis_id,
        event_type=f"hypothesis.{decision}",
        payload={"status": status.value, "analystDecision": decision, "analystNote": note},
        actor="analyst",
    )
    _, base = HYPOTHESIS_INDEX[hypothesis_id]
    return _hypothesis_with_ledger(base)


@app.post("/api/hypotheses/{hypothesis_id}/confirm")
def confirm_hypothesis(hypothesis_id: str, body: AnalystActionRequest):
    return _record_hypothesis_action(hypothesis_id, AssertionStatus.ANALYST_CONFIRMED, "confirmed", body.analystNote)


@app.post("/api/hypotheses/{hypothesis_id}/reject")
def reject_hypothesis(hypothesis_id: str, body: AnalystActionRequest):
    return _record_hypothesis_action(hypothesis_id, AssertionStatus.ANALYST_REJECTED, "rejected", body.analystNote)


@app.post("/api/hypotheses/{hypothesis_id}/request-evidence")
def request_more_evidence(hypothesis_id: str, body: AnalystActionRequest):
    return _record_hypothesis_action(hypothesis_id, AssertionStatus.NEEDS_MORE_EVIDENCE, "needs_more_evidence", body.analystNote)


class ComplianceReviewRequest(BaseModel):
    legalAccessBasis: LegalAccessBasis
    solicitationReview: SolicitationReviewStatus
    suppressionChecked: bool


@app.post("/api/parties/{party_id}/compliance-review")
def compliance_review(party_id: str, body: ComplianceReviewRequest):
    if party_id not in PARTY_INDEX:
        raise HTTPException(404, f"Unknown party: {party_id}")
    append_entry(
        aggregate_type="party",
        aggregate_id=party_id,
        event_type="party.compliance_reviewed",
        payload=body.model_dump(mode="json"),
        actor="compliance_analyst",
    )
    _, base = PARTY_INDEX[party_id]
    p = _party_with_ledger(base)
    eligible = (
        p.legalAccessBasis != LegalAccessBasis.NOT_ESTABLISHED
        and p.solicitationReview == SolicitationReviewStatus.CLEARED_BY_COUNSEL
        and p.suppressionChecked
    )
    return {**p.model_dump(), "contactEligible": eligible}


@app.get("/api/incidents/{incident_id}/linked-parties")
def linked_parties(incident_id: str):
    if incident_id not in INCIDENTS:
        raise HTTPException(404, f"Unknown incident: {incident_id}")
    target = INCIDENTS[incident_id]
    if not target.carrierDesc:
        return []
    links = []
    for other in INCIDENTS.values():
        if other.id == target.id or other.carrierDesc != target.carrierDesc:
            continue
        for p in other.parties:
            links.append({"partyId": p.id, "role": p.role, "sharedWithIncident": other.id, "linkBasis": f"Matching carrier description: '{target.carrierDesc}'"})
    return links


@app.get("/api/ledger")
def ledger_entries():
    return [e.model_dump() for e in list_entries()]


@app.get("/api/ledger/verify")
def ledger_verify():
    return {"valid": verify_chain(), "entries": len(list_entries())}


@app.get("/")
def root():
    return {
        "name": "G-CCI Consolidated Backend",
        "version": "1.1.0-demo",
        "status": "DEMO ONLY — synthetic data; frontend API contract active; ledger-backed mutations enabled",
        "incidents": len(INCIDENTS),
        "routes": ["GET /api/incidents", "GET /api/incidents/{id}", "GET /api/incidents/{id}/explain", "POST /api/hypotheses/{id}/confirm|reject|request-evidence", "POST /api/parties/{id}/compliance-review", "GET /api/ledger/verify"],
    }
