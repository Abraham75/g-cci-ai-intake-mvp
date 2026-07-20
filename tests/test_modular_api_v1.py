from fastapi.testclient import TestClient
from app.production import app

client = TestClient(app)


def test_health():
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_truck_intake_returns_strict_contract():
    response = client.post("/api/v1/intake", json={
        "state": "GA",
        "truck_involved": True,
        "hospitalization": True,
        "edr_available": True,
        "clear_liability": True,
        "incident_date": "2026-07-01"
    })
    assert response.status_code == 200
    body = response.json()
    assert body["route"] == "TRUCK"
    assert body["lead_confidence"] >= 70
    assert body["case_file_id"] is not None
    assert "compliance_trace" in body


def test_score_explain_and_compliance_are_independent_endpoints():
    payload = {"state": "GA", "truck_involved": True, "mentions_fmcsa_violation": True}
    score = client.post("/api/v1/score", json=payload)
    explain = client.post("/api/v1/explain", json=payload)
    compliance = client.post("/api/v1/compliance-trace", json=payload)
    assert score.status_code == 200
    assert explain.status_code == 200
    assert compliance.status_code == 200
    assert score.json()["route"] == "TRUCK"
    assert "explain" in explain.json()
    assert "fmcsa_relevance" in compliance.json()["filters_applied"]


def test_existing_incident_api_remains_available():
    response = client.get("/api/incidents/PhillipsIncident")
    assert response.status_code == 200
    assert response.json()["id"] == "PhillipsIncident"
