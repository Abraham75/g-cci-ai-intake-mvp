from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_incident_contract_and_reconciled_uncertainty():
    phillips = client.get("/api/incidents/PhillipsIncident")
    assert phillips.status_code == 200
    p = phillips.json()
    assert p["scores"]["uncertaintyPenalty"] == 0.0
    assert set(p["confidence"]) == {"eventCorrelation", "causalRelationship", "partyAttribution"}

    event = client.get("/api/incidents/Event5122820")
    assert event.status_code == 200
    e = event.json()
    assert e["scores"]["uncertaintyPenalty"] == 0.22
    assert e["tier"] == "C"


def test_hypothesis_action_is_ledger_backed_and_machine_confidence_is_preserved():
    before = client.get("/api/incidents/PhillipsIncident").json()
    hypothesis = before["hypotheses"][0]
    original_confidence = hypothesis["confidence"]

    result = client.post(
        f"/api/hypotheses/{hypothesis['id']}/confirm",
        json={"analystNote": "test confirmation"},
    )
    assert result.status_code == 200
    assert result.json()["confidence"] == original_confidence
    assert result.json()["status"] == "AnalystConfirmed"

    after = client.get("/api/incidents/PhillipsIncident").json()
    assert after["hypotheses"][0]["confidence"] == original_confidence
    assert after["hypotheses"][0]["analystDecision"] == "confirmed"

    ledger = client.get("/api/ledger/verify").json()
    assert ledger["valid"] is True
    assert ledger["entries"] >= 1


def test_party_compliance_review_is_ledger_backed():
    result = client.post(
        "/api/parties/party_001/compliance-review",
        json={
            "legalAccessBasis": "PublicRecord",
            "solicitationReview": "ClearedByCounsel",
            "suppressionChecked": True,
        },
    )
    assert result.status_code == 200
    assert result.json()["contactEligible"] is True

    incident = client.get("/api/incidents/PhillipsIncident").json()
    party = incident["parties"][0]
    assert party["legalAccessBasis"] == "PublicRecord"
    assert party["solicitationReview"] == "ClearedByCounsel"
    assert party["suppressionChecked"] is True
