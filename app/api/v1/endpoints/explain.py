from fastapi import APIRouter
from app.schemas.intake_v1 import IntakeRequest
from app.services.explain_service import ExplainService

router = APIRouter()
service = ExplainService()


@router.post("/explain")
async def explain(payload: IntakeRequest) -> dict:
    return service.explain(payload.model_dump())
