import math

TRUCK_TYPES = {
    "18-wheeler", "tractor-trailer",
    "commercial truck", "box truck", "bus/fleet"
}

SEVERITY_WEIGHT = {
    "moderate": 0.5,
    "high": 0.8,
    "catastrophic": 1.0
}

DEFENDANT_BONUS = {
    "National Carrier": 18,
    "Mega Carrier": 22,
    "Fortune 500": 20,
    "Regional Fleet": 10,
    "Individual/Small Biz": 4
}

COUNTY_BONUS = {
    "Cobb": 10, "Spalding": 8, "Lowndes": 8,
    "Fulton": 7, "DeKalb": 6, "Gwinnett": 5, "Clayton": 4
}

def route_submodel(incident_type: str) -> str:
    return "TRUCK_SUBMODEL" if incident_type in TRUCK_TYPES else "NON_TRUCK_SUBMODEL"

def _sigmoid(x: float) -> float:
    return 1 / (1 + math.exp(-x))

def score_truck(intake):
    base = 55
    base += int(30 * SEVERITY_WEIGHT[intake.severity])
    base += DEFENDANT_BONUS.get(intake.defendant_type, 6)
    base += COUNTY_BONUS.get(intake.county, 3)

    if intake.hours_of_service_flag:
        base += 10
    if intake.fmcsa_signal:
        base += 8
    if intake.police_report_available:
        base += 4

    lead_score = min(99, base)

    conf_raw = (
        0.9 * SEVERITY_WEIGHT[intake.severity]
        + 0.3 * (DEFENDANT_BONUS.get(intake.defendant_type, 6) / 22)
    )
    confidence = int(99 * _sigmoid((conf_raw - 0.7) * 4))

    if lead_score >= 90:
        value = "$2.5M – $5M+"
    elif lead_score >= 80:
        value = "$1.0M – $2.5M"
    elif lead_score >= 65:
        value = "$350K – $1.0M"
    else:
        value = "$150K – $350K"

    return lead_score, confidence, value

def score_non_truck(intake):
    base = 40
    base += int(25 * SEVERITY_WEIGHT[intake.severity])
    base += COUNTY_BONUS.get(intake.county, 2)

    if intake.incident_type in ("motorcycle", "pedestrian", "bicycle"):
        base += 10

    lead_score = min(89, base)
    confidence = int(99 * _sigmoid((SEVERITY_WEIGHT[intake.severity] - 0.6) * 4))

    if lead_score >= 80:
        value = "$600K – $1.2M"
    elif lead_score >= 65:
        value = "$250K – $600K"
    else:
        value = "$50K – $250K"

    return lead_score, confidence, value
