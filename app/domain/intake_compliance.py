from app.domain.intake_models import ComplianceTrace


class ComplianceEngine:
    def __init__(self):
        self.sources = [
            "GA Tort Law corpus",
            "FMCSA regulations corpus",
            "GA trucking case law corpus",
            "Advertising and ethics filters",
        ]

    def trace(self, lead: dict) -> ComplianceTrace:
        filters: list[str] = []
        notes: list[str] = []

        if not lead.get("incident_date"):
            filters.append("missing_incident_date")
            notes.append("Incident date missing; confidence should be reduced.")
        if lead.get("is_advertising_request"):
            filters.append("advertising_review")
            notes.append("Advertising content requires manual review.")
        if lead.get("state") and lead["state"] != "GA":
            filters.append("non_ga_jurisdiction")
            notes.append("Outside Georgia; local corpus may be less predictive.")
        if lead.get("mentions_fmcsa_violation"):
            filters.append("fmcsa_relevance")
            notes.append("Potential FMCSA relevance detected.")

        return ComplianceTrace(self.sources, filters, notes)
