from __future__ import annotations
from datetime import date
from typing import Any, Optional
from pydantic import BaseModel, Field


class IntakeRequest(BaseModel):
    client_name: Optional[str] = None
    incident_date: Optional[date] = None
    state: str = Field(default="GA", min_length=2, max_length=2)
    venue: Optional[str] = None
    truck_involved: bool = False
    fatality: bool = False
    hospitalization: bool = False
    edr_available: bool = False
    clear_liability: bool = False
    multiple_vehicles: bool = False
    commercial_policy_limits: Optional[float] = Field(default=None, ge=0)
    fraud_flags: bool = False
    dismissed: bool = False
    compliance_risk: bool = False
    missing_key_fields: bool = False
    is_advertising_request: bool = False
    mentions_fmcsa_violation: bool = False
    gross_vehicle_weight: Optional[float] = Field(default=None, ge=0)
    commercial_vehicle: bool = False
    raw: dict[str, Any] = Field(default_factory=dict)


class IntakeResponse(BaseModel):
    lead_id: str
    route: str
    lead_confidence: int
    expected_case_value: str
    alerts: list[dict[str, str]]
    explain: list[dict[str, Any]]
    compliance_trace: dict[str, Any]
    case_file_id: str | None = None
