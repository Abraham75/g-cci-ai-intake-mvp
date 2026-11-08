"""Authorization regression tests for the attorney feedback boundary."""
from starlette.requests import Request

from gcci.auth_middleware import _allowed
from gcci.security import Actor


def request(method: str, path: str) -> Request:
    return Request({"type": "http", "method": method, "path": path,
                    "query_string": b"", "headers": [], "scheme": "https",
                    "server": ("test", 443)})


def test_only_attorney_or_admin_can_write_ground_truth():
    paths = [
        "/hypotheses/h1/attorney-review",
        "/hypotheses/h1/outcomes",
        "/validation/benchmark-cases",
        "/validation/benchmark-cases/b1/match",
    ]
    for path in paths:
        for role in ("SERVICE", "INVESTIGATOR", "COMPLIANCE", "AUDITOR"):
            assert not _allowed(Actor(name="test", role=role), request("POST", path))
        for role in ("ATTORNEY", "ADMIN"):
            assert _allowed(Actor(name="test", role=role), request("POST", path))


def test_auditor_can_read_but_not_mutate_validation():
    actor = Actor(name="audit", role="AUDITOR")
    assert _allowed(actor, request("GET", "/validation/metrics"))
    assert _allowed(actor, request("GET", "/validation/benchmark-cases"))
    assert not _allowed(actor, request("POST", "/validation/benchmark-cases"))


def test_service_can_ingest_but_not_forge_reviews():
    actor = Actor(name="worker", role="SERVICE")
    assert _allowed(actor, request("POST", "/events/ingest"))
    assert not _allowed(actor, request("POST", "/hypotheses/h1/attorney-review"))
