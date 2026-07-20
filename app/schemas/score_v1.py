from pydantic import BaseModel
from app.schemas.intake_v1 import IntakeRequest


class ScoreRequest(IntakeRequest):
    pass


class ScoreResponse(BaseModel):
    lead_id: str
    route: str
    lead_confidence: int
    expected_case_value: str
