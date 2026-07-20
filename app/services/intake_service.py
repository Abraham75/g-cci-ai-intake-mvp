from uuid import uuid4
from app.domain.intake_scoring import DecisionEngine
from app.ledger import append_entry


class IntakeService:
    def __init__(self):
        self.engine = DecisionEngine()

    def process(self, lead: dict) -> dict:
        result = self.engine.score(lead)
        result["case_file_id"] = str(uuid4()) if result["lead_confidence"] >= 70 and result["route"] != "REJECT" else None
        append_entry(
            entity_type="lead",
            entity_id=result["lead_id"],
            action="intake_scored",
            payload={
                "route": result["route"],
                "lead_confidence": result["lead_confidence"],
                "expected_case_value": result["expected_case_value"],
                "case_file_id": result["case_file_id"],
            },
            actor="system:intake_service",
        )
        return result
