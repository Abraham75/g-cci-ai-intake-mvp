from app.domain.intake_models import ExplainRow, LeadRoute


class ExplainEngine:
    def explain(self, lead: dict, route: LeadRoute) -> list[ExplainRow]:
        rows: list[ExplainRow] = []
        if lead.get("truck_involved"):
            rows.append(ExplainRow("truck_involved", 0.38, "Commercial truck involvement increases catastrophic exposure."))
        if lead.get("fatality"):
            rows.append(ExplainRow("fatality", 0.30, "Fatal injury sharply increases damages and urgency."))
        if lead.get("edr_available"):
            rows.append(ExplainRow("edr_available", 0.12, "EDR or telematics may strengthen liability proof."))
        if lead.get("multiple_vehicles"):
            rows.append(ExplainRow("multiple_vehicles", 0.10, "Multi-vehicle collisions can expand fault and coverage analysis."))
        if lead.get("clear_liability"):
            rows.append(ExplainRow("clear_liability", 0.10, "Clear liability increases case confidence."))
        if route == LeadRoute.REJECT:
            rows.append(ExplainRow("quality_or_compliance_risk", -0.50, "Risk profile warrants rejection or manual review."))
        return rows
