from datetime import datetime, timezone

from gcci.correlation import build_incident_hypotheses, correlate_pair
from gcci.models import GeoPoint, NormalizedEvent, Provenance, SourceKind


def event(id: str, source: str, minute: int, lat: float, lon: float, direction: str = "WB", description: str = "Crash involving box truck, EMS responding") -> NormalizedEvent:
    return NormalizedEvent(
        id=id,
        source_kind=SourceKind.GDOT_511 if source == "GDOT" else SourceKind.GEMA_WAZE,
        observed_at=datetime(2026, 1, 1, 12, minute, tzinfo=timezone.utc),
        reported_at=datetime(2026, 1, 1, 12, minute, tzinfo=timezone.utc),
        point=GeoPoint(latitude=lat, longitude=lon),
        roadway="I-285",
        direction=direction,
        event_type="CRASH",
        description=description,
        commercial_vehicle_hint=True,
        injury_hint=True,
        provenance=Provenance(source_system=source, source_record_id=id),
    )


def test_same_incident_cross_source() -> None:
    a = event("a", "GDOT", 0, 33.91, -84.37)
    b = event("b", "GEMA", 2, 33.9105, -84.3705)
    result = correlate_pair(a, b)
    assert result.score >= 0.82


def test_direction_conflict_is_exposed() -> None:
    a = event("a", "GDOT", 0, 33.91, -84.37, "WB")
    b = event("b", "GEMA", 1, 33.9102, -84.3702, "EB")
    result = correlate_pair(a, b)
    assert result.contradictions


def test_clusters_related_records() -> None:
    events = [
        event("a", "GDOT", 0, 33.91, -84.37),
        event("b", "GEMA", 2, 33.9104, -84.3703),
        event("c", "GDOT", 45, 34.2, -84.6),
    ]
    hypotheses, _ = build_incident_hypotheses(events)
    assert any(set(h.member_event_ids) == {"a", "b"} for h in hypotheses)
