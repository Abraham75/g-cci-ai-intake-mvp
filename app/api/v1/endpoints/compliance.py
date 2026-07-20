from fastapi import APIRouter
from app.schemas.intake_v1 import IntakeRequest
from app.services.compliance_service import ComplianceService

router = APIRouter()
service = ComplianceService()


@router.post("/compliance-trace")
async def compliance_trace(payload: IntakeRequest) -> dict:
    return service.trace(payload.model_dump())
