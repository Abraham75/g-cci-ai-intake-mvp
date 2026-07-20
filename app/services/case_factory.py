from uuid import uuid4


class CaseFactory:
    def create_case_file(self, *, lead_id: str, route: str, lead_confidence: int) -> dict:
        return {
            "case_file_id": str(uuid4()),
            "lead_id": lead_id,
            "route": route,
            "lead_confidence": lead_confidence,
            "status": "PENDING_ATTORNEY_REVIEW",
        }
