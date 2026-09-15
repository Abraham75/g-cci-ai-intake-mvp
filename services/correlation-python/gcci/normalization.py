from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
import re

from .models import GeoPoint, NormalizedEvent, Provenance, SourceKind
from .utils import normalize_direction, normalize_roadway, stable_hash

COMMERCIAL_PATTERNS = re.compile(r"\b(tractor[- ]?trailer|semi|18[- ]?wheeler|commercial vehicle|box truck|dump truck|work truck|motor carrier|truck tractor|bobtail|bus)\b", re.I)
INJURY_PATTERNS = re.compile(r"\b(injur|ems|ambulance|hospital|medic|transported)\w*\b", re.I)
FATALITY_PATTERNS = re.compile(r"\b(fatal|death|deceased|killed)\w*\b", re.I)
DEBRIS_PATTERNS = re.compile(r"\b(debris|object in road|road debris|tire in road)\b", re.I)
WHEEL_OFF_PATTERNS = re.compile(r"\b(wheel[- ]?off|wheel detach|tire (fell|came) off|lost wheel)\b", re.I)
CLOSURE_PATTERNS = re.compile(r"\b(all lanes.*closed|full closure|road closed|blocked)\b", re.I)
STALL_PATTERNS = re.compile(r"\b(stall|disabled vehicle|vehicle stopped)\w*\b", re.I)


def parse_datetime(value: Any) -> datetime | None:
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    if isinstance(value, (int, float)):
        n = float(value)
        if n > 10_000_000_000:
            n /= 1000
        return datetime.fromtimestamp(n, tz=timezone.utc)
    if isinstance(value, str):
        text = value.strip().replace("Z", "+00:00")
        try:
            dt = datetime.fromisoformat(text)
            return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
        except ValueError:
            return None
    return None


def _text(*values: Any) -> str | None:
    for value in values:
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def _number(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def infer_hints(description: str) -> dict[str, bool]:
    return {
        "commercial_vehicle_hint": bool(COMMERCIAL_PATTERNS.search(description)),
        "injury_hint": bool(INJURY_PATTERNS.search(description)),
        "fatality_hint": bool(FATALITY_PATTERNS.search(description)),
        "closure_hint": bool(CLOSURE_PATTERNS.search(description)),
        "stalled_vehicle_hint": bool(STALL_PATTERNS.search(description)),
        "debris_hint": bool(DEBRIS_PATTERNS.search(description)),
        "wheel_off_hint": bool(WHEEL_OFF_PATTERNS.search(description)),
    }


def normalize_generic_record(*, source_kind: SourceKind, source_system: str, source_record_id: str, observed_at: datetime, event_type: str, description: str, roadway: str | None = None, direction: str | None = None, latitude: float | None = None, longitude: float | None = None, location_text: str | None = None, reported_at: datetime | None = None, updated_at: datetime | None = None, lanes_affected: str | None = None, source_url: str | None = None, raw: dict[str, Any] | None = None, attributes: dict[str, str] | None = None) -> NormalizedEvent:
    raw = raw or {}
    point = GeoPoint(latitude=latitude, longitude=longitude) if latitude is not None and longitude is not None else None
    return NormalizedEvent(
        id=f"{source_system}:{source_record_id}",
        source_kind=source_kind,
        observed_at=observed_at,
        reported_at=reported_at,
        updated_at=updated_at,
        point=point,
        roadway=normalize_roadway(roadway),
        direction=normalize_direction(direction),
        location_text=location_text,
        event_type=event_type,
        description=description,
        lanes_affected=lanes_affected,
        attributes=attributes or {},
        provenance=Provenance(source_system=source_system, source_record_id=source_record_id, source_url=source_url, raw_sha256=stable_hash(raw)),
        raw=raw,
        **infer_hints(description),
    )


def normalize_gdot_511_event(row: dict[str, Any], source_url: str | None = None) -> NormalizedEvent:
    description = _text(row.get("Description"), row.get("EventType"), row.get("Type")) or "Traffic event"
    source_record_id = str(row.get("ID") or row.get("Id") or row.get("SourceId") or stable_hash(row)[:16])
    return normalize_generic_record(
        source_kind=SourceKind.GDOT_511,
        source_system="GDOT_511",
        source_record_id=source_record_id,
        observed_at=datetime.now(timezone.utc),
        reported_at=parse_datetime(row.get("Reported") or row.get("StartDate")),
        updated_at=parse_datetime(row.get("LastUpdated") or row.get("Updated")),
        event_type=_text(row.get("EventType"), row.get("Type")) or "UNKNOWN",
        description=description,
        roadway=_text(row.get("RoadwayName"), row.get("Roadway")),
        direction=_text(row.get("DirectionOfTravel"), row.get("Direction")),
        latitude=_number(row.get("Latitude")),
        longitude=_number(row.get("Longitude")),
        location_text=_text(row.get("Location")),
        lanes_affected=_text(row.get("LanesAffected"), row.get("Lanes")),
        source_url=source_url,
        raw=row,
    )


def normalize_arcgis_feature(feature: dict[str, Any], *, source_system: str, source_kind: SourceKind, source_url: str | None = None) -> NormalizedEvent:
    props = feature.get("properties") or feature.get("attributes") or {}
    geom = feature.get("geometry") or {}
    lat = lon = None
    if geom.get("type") == "Point":
        coords = geom.get("coordinates") or []
        if len(coords) >= 2:
            lon, lat = _number(coords[0]), _number(coords[1])
    else:
        lat, lon = _number(geom.get("y")), _number(geom.get("x"))

    description = _text(props.get("DESCRIPTION"), props.get("Description"), props.get("DESCRIPTIO"), props.get("TYPE"), props.get("EVENT_TYPE"), props.get("subtype")) or "Traffic event"
    source_record_id = str(props.get("OBJECTID") or props.get("EVENT_ID") or props.get("ID") or feature.get("id") or stable_hash(feature)[:16])
    return normalize_generic_record(
        source_kind=source_kind,
        source_system=source_system,
        source_record_id=source_record_id,
        observed_at=datetime.now(timezone.utc),
        event_type=_text(props.get("TYPE"), props.get("EVENT_TYPE"), props.get("type")) or "UNKNOWN",
        description=description,
        roadway=_text(props.get("ROUTE"), props.get("ROADWAY"), props.get("ROAD_NAME"), props.get("street")),
        direction=_text(props.get("DIRECTION"), props.get("DIR"), props.get("direction")),
        latitude=lat,
        longitude=lon,
        location_text=_text(props.get("LOCATION"), props.get("COUNTY_NAME"), props.get("location")),
        source_url=source_url,
        raw=feature,
    )
