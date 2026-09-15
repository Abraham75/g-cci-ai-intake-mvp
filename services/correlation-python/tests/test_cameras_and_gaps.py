from datetime import datetime, timezone

from gcci.cameras import find_nearest_cameras
from gcci.evidence_gaps import rank_evidence_gaps
from gcci.models import Camera, CorrelationClass, GeoPoint, IncidentHypothesis, NormalizedEvent, Provenance, SourceKind


def test_nearest_camera_and_gap_priority() -> None:
    hyp = IncidentHypothesis(
        id="h1",
        member_event_ids=["e1"],
        machine_confidence=0.9,
        classification=CorrelationClass.SAME_INCIDENT,
        rationale=["test"],
        centroid=GeoPoint(latitude=33.91, longitude=-84.37),
        start_time=datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc),
        end_time=datetime(2026, 1, 1, 12, 1, tzinfo=timezone.utc),
        roadway="I-285",
        direction="WB",
    )
    camera = Camera(
        id="cam1",
        name="I-285 @ Roswell Rd",
        point=GeoPoint(latitude=33.9102, longitude=-84.3701),
        roadway="I-285",
        direction="WB",
    )
    event = NormalizedEvent(
        id="e1",
        source_kind=SourceKind.GDOT_511,
        observed_at=datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc),
        point=GeoPoint(latitude=33.91, longitude=-84.37),
        roadway="I-285",
        direction="WB",
        event_type="CRASH",
        description="Wheel off commercial truck, EMS responding",
        commercial_vehicle_hint=True,
        injury_hint=True,
        wheel_off_hint=True,
        provenance=Provenance(source_system="GDOT", source_record_id="1"),
    )

    cameras = find_nearest_cameras(hyp, [camera])
    assert cameras and cameras[0].camera.id == "cam1"

    gaps = rank_evidence_gaps(hyp, [event], cameras)
    assert gaps[0].expected_information_gain > 0
    assert any(g.evidence_type == "CCTV" for g in gaps)
