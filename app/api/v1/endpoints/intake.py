from fastapi import APIRouter
from app.schemas.intake_v1 import IntakeRequest, IntakeResponse
from app.services.intake_service import IntakeService

router = APIRouter()
service = IntakeService()


@router.post("/intake", response_model=IntakeResponse)
async def intake(payload: IntakeRequest) -> IntakeResponse:
    return IntakeResponse(**service.process(payload.model_dump()))
