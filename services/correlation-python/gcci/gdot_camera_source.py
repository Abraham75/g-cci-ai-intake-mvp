from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import httpx
from sqlalchemy import text

from .camera_repository import upsert_camera_inventory
from .config import Settings, settings
from .database import SessionLocal
from .models import Camera, GeoPoint, Provenance
from .utils import stable_hash


SOURCE_SYSTEM = "GDOT_ARCGIS_CAMERA"


def _pick(properties: dict[str, Any], *keys: str) -> str | None:
    for key in keys:
        value = properties.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def parse_gdot_camera_geojson(body: dict[str, Any]) -> list[Camera]:
    features = body.get("features") if isinstance(body, dict) else None
    if not isinstance(features, list):
        return []

    cameras: list[Camera] = []
    for feature in features:
        if not isinstance(feature, dict):
            continue
        properties = feature.get("properties") or {}
        geometry = feature.get("geometry") or {}
        coordinates = geometry.get("coordinates") if geometry.get("type") == "Point" else None
        if not isinstance(properties, dict) or not isinstance(coordinates, list) or len(coordinates) < 2:
            continue
        try:
            longitude = float(coordinates[0])
            latitude = float(coordinates[1])
        except (TypeError, ValueError):
            continue
        if not (-180 <= longitude <= 180 and -90 <= latitude <= 90):
            continue

        external_id = str(
            properties.get("OBJECTID")
            or properties.get("DEVICE_ID")
            or properties.get("DEVICE_NAME")
            or feature.get("id")
            or ""
        ).strip()
        if not external_id:
            continue

        name = _pick(properties, "DEVICE_NAME", "CAMERA_NAME", "NAME") or f"GDOT Camera {external_id}"
        source_record_id = external_id
        raw_hash = stable_hash({"properties": properties, "geometry": geometry})
        cameras.append(
            Camera(
                id=f"gdot-arcgis:{external_id}",
                name=name,
                point=GeoPoint(latitude=latitude, longitude=longitude),
                roadway=_pick(properties, "ROADWAY", "ROUTE", "ROAD_NAME"),
                direction=_pick(properties, "DIRECTION", "DIR"),
                snapshot_url=_pick(properties, "SNAPSHOT_URL", "IMAGE_URL", "CAMERA_URL", "URL"),
                stream_url=_pick(properties, "STREAM_URL", "VIDEO_URL"),
                source_system=SOURCE_SYSTEM,
                provenance=Provenance(
                    source_system=SOURCE_SYSTEM,
                    source_record_id=source_record_id,
                    source_url=settings.gdot_camera_arcgis_url,
                    retrieved_at=datetime.now(timezone.utc),
                    raw_sha256=raw_hash,
                ),
            )
        )
    return cameras


async def fetch_gdot_camera_inventory(cfg: Settings = settings) -> list[Camera]:
    params = {
        "where": "1=1",
        "outFields": "*",
        "f": "geojson",
        "outSR": "4326",
        "returnGeometry": "true",
    }
    timeout = httpx.Timeout(cfg.source_timeout_seconds)
    async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
        response = await client.get(
            cfg.gdot_camera_arcgis_url,
            params=params,
            headers={"Accept": "application/geo+json, application/json"},
        )
        response.raise_for_status()
        body = response.json()
    cameras = parse_gdot_camera_geojson(body)
    if len(cameras) < cfg.camera_min_expected_records:
        raise RuntimeError(
            f"GDOT camera snapshot contained only {len(cameras)} valid cameras; "
            f"minimum expected is {cfg.camera_min_expected_records}. Existing inventory retained."
        )
    return cameras


async def refresh_gdot_camera_inventory(cfg: Settings = settings) -> int:
    """Atomically replace active GDOT ArcGIS inventory after a validated fetch.

    Source failure or suspiciously small snapshots occur before the database transaction,
    so they never deactivate the last known-good inventory.
    """
    cameras = await fetch_gdot_camera_inventory(cfg)
    async with SessionLocal() as session:
        async with session.begin():
            await session.execute(
                text(
                    """
                    UPDATE traffic_cameras
                    SET active = false
                    WHERE source_system = :source_system
                    """
                ),
                {"source_system": SOURCE_SYSTEM},
            )
            count = await upsert_camera_inventory(
                session,
                cameras,
                produced_by="camera.gdotArcgisRefresh",
            )
    return count
