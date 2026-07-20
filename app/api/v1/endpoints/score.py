from fastapi import APIRouter
from app.schemas.score_v1 import ScoreRequest, ScoreResponse
from app.services.decision_service import DecisionService

router = APIRouter()
service = DecisionService()


@router.post("/score", response_model=ScoreResponse)
async def score(payload: ScoreRequest) -> ScoreResponse:
    result = service.score(payload.model_dump())
    return ScoreResponse(**result)
