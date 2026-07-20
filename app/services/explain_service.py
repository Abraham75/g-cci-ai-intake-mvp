from app.domain.intake_scoring import DecisionEngine


class ExplainService:
    def __init__(self):
        self.engine = DecisionEngine()

    def explain(self, lead: dict) -> dict:
        result = self.engine.score(lead)
        return {
            "lead_id": result["lead_id"],
            "route": result["route"],
            "explain": result["explain"],
            "alerts": result["alerts"],
        }
