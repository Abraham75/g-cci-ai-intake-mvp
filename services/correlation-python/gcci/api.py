from __future__ import annotations

from fastapi import FastAPI
from pydantic import BaseModel, Field

from .models import Camera, CorrelatedIncidentPackage, NormalizedEvent
from .service import CrossSourceCorrelationService

app = FastAPI(
    title="G-CCI Cross-Source Event Correlation Service",
    version="1.0.0",
    description=(
        "Correlates normalized transportation-event records across independent sources, "
        "discovers nearby cameras, and ranks evidence-development gaps. "
        "It does not identify people or authorize attorney outreach."
    ),
)

service = CrossSourceCorrelationService()


class CorrelateRequest(BaseModel):
    events: list[NormalizedEvent] = Field(min_length=1)
    cameras: list[Camera] = Field(default_factory=list)


class CorrelateResponse(BaseModel):
    packages: list[CorrelatedIncidentPackage]
    policy: dict[str, object]


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "gcci-cross-source-correlation"}


@app.post("/correlate", response_model=CorrelateResponse)
def correlate(body: CorrelateRequest) -> CorrelateResponse:
    packages = service.analyze(body.events, body.cameras)
    return CorrelateResponse(
        packages=packages,
        policy={
            "personIdentification": False,
            "partyAttributionPerformed": False,
            "contactEligibilityEvaluated": False,
            "requiresComplianceGateBeforeOutreach": True,
        },
    )
