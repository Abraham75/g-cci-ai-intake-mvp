from app.main import app
from app.api.v1.router import api_router
from app.core.config import settings

# Preserve the consolidated incident-intelligence API and mount the new
# modular intake/scoring/explainability/compliance API alongside it.
app.title = settings.PROJECT_NAME
app.version = settings.VERSION
app.description = (
    "G-CCI modular monolith combining incident intelligence, case-opportunity "
    "analytics, intake scoring, explainability, compliance tracing, and ledger-backed decisions."
)
app.include_router(api_router, prefix=settings.API_V1_PREFIX)
