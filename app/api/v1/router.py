from fastapi import APIRouter
from app.api.v1.endpoints.health import router as health_router
from app.api.v1.endpoints.intake import router as intake_router
from app.api.v1.endpoints.score import router as score_router
from app.api.v1.endpoints.explain import router as explain_router
from app.api.v1.endpoints.compliance import router as compliance_router

api_router = APIRouter()
api_router.include_router(health_router, tags=["health"])
api_router.include_router(intake_router, tags=["intake"])
api_router.include_router(score_router, tags=["score"])
api_router.include_router(explain_router, tags=["explain"])
api_router.include_router(compliance_router, tags=["compliance"])
