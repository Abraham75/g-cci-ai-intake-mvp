from schemas import ShapBar, ComplianceTrace, ExplainResponse
from compliance import RAG_CORPUS, evaluate_compliance

def build_shap_bars(intake, model_path):
    bars = []

    if model_path == "TRUCK_SUBMODEL":
        bars.append(ShapBar("Truck involvement", 0.30, "up"))
        if intake.hours_of_service_flag:
            bars.append(ShapBar("Driver fatigue (HOS)", 0.20, "up"))

    bars.append(ShapBar(f"Injury severity: {intake.severity}", 0.25, "up"))
    bars.append(ShapBar(f"Venue: {intake.county}", 0.10, "up"))

    if not intake.police_report_available:
        bars.append(ShapBar("No police report yet", -0.08, "down"))

    return bars

def build_explain(intake, model_path, lead_score):
    text = (
        f"Lead routed to {model_path} based on incident type. "
        f"Primary drivers include injury severity, venue strength, "
        f"and defendant sophistication. Informational only."
    )

    status, filters_passed, flags = evaluate_compliance(text)

    return ExplainResponse(
        model_path=model_path,
        plain_english=text,
        shap_bars=build_shap_bars(intake, model_path),
        compliance_trace=ComplianceTrace(
            rag_corpus=RAG_CORPUS,
            filters_passed=filters_passed,
            flags=flags,
            status=status
        )
    )
