from pydantic import BaseModel, Field
from typing import Literal, Optional, List, Dict

IncidentType = Literal[
    "18-wheeler", "tractor-trailer", "commercial truck",
    "box truck", "bus/fleet",
    "auto", "motorcycle", "pedestrian", "bicycle"
]

Severity = Literal["moderate", "high", "catastrophic"]

County = Literal[
    "Cobb", "Spalding", "Lowndes", "Fulton",
    "DeKalb", "Gwinnett", "Clayton"
]

DefendantType = Literal[
    "National Carrier", "Mega Carrier",
    "Fortune 500", "Regional Fleet",
    "Individual/Small Biz"
]

class IntakeRequest(BaseModel):
    client_name: str = Field(..., min_length=2, max_length=80)
    incident_type: IncidentType
    severity: Severity
    county: County
    defendant: str
    defendant_type: DefendantType

    fmcsa_signal: Optional[bool] = False
    hours_of_service_flag: Optional[bool] = False
    cdl_driver_involved: Optional[bool] = False
    police_report_available: Optional[bool] = False

class ShapBar(BaseModel):
    feature: str
    contribution: float
    direction: Literal["up", "down"]

class ComplianceTrace(BaseModel):
    rag_corpus: List[str]
    filters_passed: List[str]
    flags: List[str]
    status: Literal["PASS", "REVIEW", "BLOCK"]

class ExplainResponse(BaseModel):
    model_path: Literal["TRUCK_SUBMODEL", "NON_TRUCK_SUBMODEL"]
    plain_english: str
    shap_bars: List[ShapBar]
    compliance_trace: ComplianceTrace

class LeadResponse(BaseModel):
    lead_id: str
    created_ts: int
    model_path: str
    lead_score: int
    confidence: int
    expected_value_range: str
    mycase_file: str
    intake: Dict
    explain: ExplainResponse
