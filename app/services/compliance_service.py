from app.domain.intake_compliance import ComplianceEngine


class ComplianceService:
    def __init__(self):
        self.engine = ComplianceEngine()

    def trace(self, lead: dict) -> dict:
        trace = self.engine.trace(lead)
        return {
            "sources": trace.sources,
            "filters_applied": trace.filters_applied,
            "notes": trace.notes,
        }
