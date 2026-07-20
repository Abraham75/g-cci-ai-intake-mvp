from decimal import Decimal
from uuid import uuid4
from app.domain.intake_compliance import ComplianceEngine
from app.domain.intake_explainability import ExplainEngine
from app.domain.intake_models import Alert, AlertLevel, LeadRoute


def money(value) -> Decimal:
    return Decimal(str(value)).quantize(Decimal("0.01"))


class DecisionEngine:
    def __init__(self):
        self.compliance = ComplianceEngine()
        self.explainer = ExplainEngine()

    def route_case(self, lead: dict) -> LeadRoute:
        if lead.get("dismissed") or lead.get("fraud_flags"):
            return LeadRoute.REJECT
        if lead.get("truck_involved") or lead.get("gross_vehicle_weight") or lead.get("commercial_vehicle"):
            return LeadRoute.TRUCK
        return LeadRoute.NON_TRUCK_PI

    def score(self, lead: dict) -> dict:
        route = self.route_case(lead)
        compliance = self.compliance.trace(lead)

        base = 25 if route == LeadRoute.REJECT else 41 if route == LeadRoute.NON_TRUCK_PI else 62
        if lead.get("fatality"): base += 18
        if lead.get("hospitalization"): base += 12
        if lead.get("edr_available"): base += 8
        if lead.get("clear_liability"): base += 7
        if lead.get("multiple_vehicles"): base += 5
        if lead.get("compliance_risk"): base -= 15
        if lead.get("missing_key_fields"): base -= 10
        if compliance.filters_applied: base -= 5
        confidence = max(0, min(100, base))

        value = Decimal("50000")
        if route == LeadRoute.TRUCK: value = Decimal("750000")
        if lead.get("fatality"): value *= Decimal("2.2")
        if lead.get("hospitalization"): value *= Decimal("1.5")
        if lead.get("clear_liability"): value *= Decimal("1.2")
        if lead.get("commercial_policy_limits"):
            value = max(value, money(lead["commercial_policy_limits"]) * Decimal("2"))

        explain = self.explainer.explain(lead, route)
        alerts: list[Alert] = []
        if confidence >= 85:
            alerts.append(Alert(AlertLevel.CRITICAL, "High-confidence catastrophic intake"))
        elif confidence >= 70:
            alerts.append(Alert(AlertLevel.WARN, "Strong case requiring fast attorney review"))
        else:
            alerts.append(Alert(AlertLevel.INFO, "Case requires additional screening"))
        if route == LeadRoute.TRUCK and lead.get("edr_available"):
            alerts.append(Alert(AlertLevel.CRITICAL, "Preserve EDR and telematics immediately"))
        if compliance.filters_applied:
            alerts.append(Alert(AlertLevel.WARN, "Compliance review required before outreach"))

        return {
            "lead_id": str(uuid4()),
            "lead_confidence": confidence,
            "expected_case_value": str(money(value)),
            "route": route.value,
            "explain": [{"feature": r.feature, "contribution": r.contribution, "reason": r.reason} for r in explain],
            "alerts": [{"level": a.level.value, "message": a.message} for a in alerts],
            "compliance_trace": {
                "sources": compliance.sources,
                "filters_applied": compliance.filters_applied,
                "notes": compliance.notes,
            },
        }
