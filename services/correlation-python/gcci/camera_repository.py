from __future__ import annotations

import json
from datetime import timedelta
from typing import Iterable
from uuid import uuid4

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from .config import Settings, settings
from .ledger import append_ledger_entry
from .models import Camera
from .utils import normalize_direction, normalize_roadway


CAMERA_CANDIDATE_MODEL_VERSION = "gcci-camera-candidate-v1.0.0"


def _camera_payload(camera: Camera) -> dict:
    return camera.model_dump(mode="json")


async def upsert_camera_inventory(
    session: AsyncSession,
    cameras: Iterable[Camera],
    *,
    produced_by: str = "camera.inventory",
) -> int:
    """Persist a camera inventory snapshot without losing stable camera identity.

    Camera geometry is stored as PostGIS geography so hypothesis-to-camera distance
    can be computed in meters.  A refresh updates mutable metadata and last_seen_at;
    it never manufactures a camera relationship to an incident.
    """
    camera_list = list(cameras)
    for camera in camera_list:
        source_record_id = (
            camera.provenance.source_record_id
            if camera.provenance is not None
            else camera.id
        )
        raw = _camera_payload(camera)
        await session.execute(
            text(
                """
                INSERT INTO traffic_cameras (
                    id, source_system, source_record_id, name, roadway, direction,
                    latitude, longitude, geom, snapshot_url, stream_url,
                    active, raw_json, first_seen_at, last_seen_at
                )
                VALUES (
                    :id, :source_system, :source_record_id, :name, :roadway, :direction,
                    :latitude, :longitude,
                    ST_SetSRID(ST_MakePoint(:longitude, :latitude), 4326)::geography,
                    :snapshot_url, :stream_url, true, CAST(:raw_json AS jsonb), now(), now()
                )
                ON CONFLICT (id) DO UPDATE SET
                    source_system = EXCLUDED.source_system,
                    source_record_id = EXCLUDED.source_record_id,
                    name = EXCLUDED.name,
                    roadway = EXCLUDED.roadway,
                    direction = EXCLUDED.direction,
                    latitude = EXCLUDED.latitude,
                    longitude = EXCLUDED.longitude,
                    geom = EXCLUDED.geom,
                    snapshot_url = EXCLUDED.snapshot_url,
                    stream_url = EXCLUDED.stream_url,
                    active = true,
                    raw_json = EXCLUDED.raw_json,
                    last_seen_at = now()
                """
            ),
            {
                "id": camera.id,
                "source_system": camera.source_system,
                "source_record_id": source_record_id,
                "name": camera.name,
                "roadway": camera.roadway,
                "direction": camera.direction,
                "latitude": camera.point.latitude,
                "longitude": camera.point.longitude,
                "snapshot_url": camera.snapshot_url,
                "stream_url": camera.stream_url,
                "raw_json": json.dumps(raw, separators=(",", ":"), sort_keys=True),
            },
        )

    if camera_list:
        await append_ledger_entry(
            session,
            entry_type="CameraInventoryRefresh",
            subject_id="camera_inventory",
            payload={
                "action": "camera-inventory-upserted",
                "cameraCount": len(camera_list),
                "cameraIds": [camera.id for camera in camera_list[:100]],
                "cameraIdsTruncated": len(camera_list) > 100,
            },
            produced_by=produced_by,
            source_system="PostgreSQL/PostGIS",
            model_version=CAMERA_CANDIDATE_MODEL_VERSION,
        )
    return len(camera_list)


async def refresh_hypothesis_camera_candidates(
    session: AsyncSession,
    hypothesis_id: str,
    *,
    cfg: Settings = settings,
    input_entry_ids: list[str] | None = None,
) -> list[dict]:
    """Materialize the nearest relevant cameras for the CURRENT hypothesis revision.

    Relevance is deliberately narrow: distance + roadway compatibility + direction
    compatibility.  It is an evidence-discovery score only; it is not causation,
    attribution, liability, or contact eligibility.
    """
    hypothesis = (
        await session.execute(
            text(
                """
                SELECT id, current_revision, start_time, end_time, roadway, direction,
                       centroid
                FROM incident_hypotheses
                WHERE id = :hypothesis_id AND active = true
                """
            ),
            {"hypothesis_id": hypothesis_id},
        )
    ).mappings().first()
    if hypothesis is None:
        raise ValueError(f"Unknown hypothesis: {hypothesis_id}")

    revision = int(hypothesis["current_revision"])
    if hypothesis["centroid"] is None:
        return []

    # Older candidate sets remain queryable but cannot masquerade as current.
    await session.execute(
        text(
            """
            UPDATE hypothesis_camera_candidates
            SET status = 'SUPERSEDED', updated_at = now()
            WHERE hypothesis_id = :hypothesis_id
              AND revision < :revision
              AND status = 'CURRENT'
            """
        ),
        {"hypothesis_id": hypothesis_id, "revision": revision},
    )
    await session.execute(
        text(
            "DELETE FROM hypothesis_camera_candidates WHERE hypothesis_id = :hypothesis_id AND revision = :revision"
        ),
        {"hypothesis_id": hypothesis_id, "revision": revision},
    )

    rows = (
        await session.execute(
            text(
                """
                SELECT c.id, c.name, c.source_system, c.roadway, c.direction,
                       c.latitude, c.longitude, c.snapshot_url, c.stream_url,
                       ST_Distance(c.geom, h.centroid) AS distance_meters
                FROM traffic_cameras c
                JOIN incident_hypotheses h ON h.id = :hypothesis_id
                WHERE c.active = true
                  AND h.centroid IS NOT NULL
                  AND ST_DWithin(c.geom, h.centroid, :radius_meters)
                ORDER BY ST_Distance(c.geom, h.centroid) ASC
                LIMIT :candidate_limit
                """
            ),
            {
                "hypothesis_id": hypothesis_id,
                "radius_meters": cfg.camera_search_radius_meters,
                # Pull a broader distance set before semantic ranking.
                "candidate_limit": max(cfg.max_camera_results * 5, cfg.max_camera_results),
            },
        )
    ).mappings().all()

    h_roadway = normalize_roadway(hypothesis["roadway"]) if hypothesis["roadway"] else None
    h_direction = normalize_direction(hypothesis["direction"]) if hypothesis["direction"] else None
    preservation_start = hypothesis["start_time"] - timedelta(
        minutes=cfg.camera_preservation_before_minutes
    )
    preservation_end = hypothesis["end_time"] + timedelta(
        minutes=cfg.camera_preservation_after_minutes
    )

    ranked: list[dict] = []
    for row in rows:
        distance = float(row["distance_meters"])
        roadway_match = bool(
            h_roadway and row["roadway"] and h_roadway == normalize_roadway(row["roadway"])
        )
        direction_match = bool(
            h_direction and row["direction"] and h_direction == normalize_direction(row["direction"])
        )
        distance_score = max(0.0, 1.0 - distance / cfg.camera_search_radius_meters)
        relevance = min(
            1.0,
            0.70 * distance_score
            + 0.20 * (1.0 if roadway_match else 0.0)
            + 0.10 * (1.0 if direction_match else 0.0),
        )
        ranked.append(
            {
                "cameraId": row["id"],
                "name": row["name"],
                "sourceSystem": row["source_system"],
                "roadway": row["roadway"],
                "direction": row["direction"],
                "latitude": float(row["latitude"]),
                "longitude": float(row["longitude"]),
                "snapshotUrl": row["snapshot_url"],
                "streamUrl": row["stream_url"],
                "distanceMeters": round(distance, 1),
                "roadwayMatch": roadway_match,
                "directionMatch": direction_match,
                "relevanceScore": round(relevance, 4),
                "preservationWindowStart": preservation_start,
                "preservationWindowEnd": preservation_end,
            }
        )

    ranked.sort(key=lambda item: item["relevanceScore"], reverse=True)
    ranked = ranked[: cfg.max_camera_results]

    for item in ranked:
        candidate_id = str(uuid4())
        await session.execute(
            text(
                """
                INSERT INTO hypothesis_camera_candidates (
                    id, hypothesis_id, revision, camera_id, distance_meters,
                    roadway_match, direction_match, relevance_score,
                    preservation_window_start, preservation_window_end,
                    status, created_at, updated_at
                ) VALUES (
                    :id, :hypothesis_id, :revision, :camera_id, :distance_meters,
                    :roadway_match, :direction_match, :relevance_score,
                    :window_start, :window_end, 'CURRENT', now(), now()
                )
                """
            ),
            {
                "id": candidate_id,
                "hypothesis_id": hypothesis_id,
                "revision": revision,
                "camera_id": item["cameraId"],
                "distance_meters": item["distanceMeters"],
                "roadway_match": item["roadwayMatch"],
                "direction_match": item["directionMatch"],
                "relevance_score": item["relevanceScore"],
                "window_start": preservation_start,
                "window_end": preservation_end,
            },
        )
        item["id"] = candidate_id
        item["hypothesisId"] = hypothesis_id
        item["revision"] = revision
        item["status"] = "CURRENT"

    await append_ledger_entry(
        session,
        entry_type="CameraCandidateSet",
        subject_id=hypothesis_id,
        payload={
            "action": "camera-candidates-refreshed",
            "hypothesisRevision": revision,
            "searchRadiusMeters": cfg.camera_search_radius_meters,
            "preservationWindowStart": preservation_start.isoformat(),
            "preservationWindowEnd": preservation_end.isoformat(),
            "candidateCount": len(ranked),
            "candidates": [
                {
                    "cameraId": item["cameraId"],
                    "distanceMeters": item["distanceMeters"],
                    "roadwayMatch": item["roadwayMatch"],
                    "directionMatch": item["directionMatch"],
                    "relevanceScore": item["relevanceScore"],
                }
                for item in ranked
            ],
            "policy": {
                "scoreMeaning": "evidence-discovery relevance only",
                "causalRelationshipInferred": False,
                "partyAttributionInferred": False,
                "contactEligibilityEvaluated": False,
            },
        },
        produced_by="camera.candidateEngine",
        source_system="PostgreSQL/PostGIS",
        model_version=CAMERA_CANDIDATE_MODEL_VERSION,
        input_entry_ids=input_entry_ids or [],
    )
    return ranked


async def camera_candidates_for_hypothesis(
    session: AsyncSession,
    hypothesis_id: str,
    *,
    current_only: bool = True,
) -> list[dict]:
    condition = "AND hc.status = 'CURRENT'" if current_only else ""
    rows = (
        await session.execute(
            text(
                f"""
                SELECT hc.id, hc.hypothesis_id, hc.revision, hc.camera_id,
                       hc.distance_meters, hc.roadway_match, hc.direction_match,
                       hc.relevance_score, hc.preservation_window_start,
                       hc.preservation_window_end, hc.status,
                       c.name, c.source_system, c.roadway, c.direction,
                       c.latitude, c.longitude, c.snapshot_url, c.stream_url
                FROM hypothesis_camera_candidates hc
                JOIN traffic_cameras c ON c.id = hc.camera_id
                WHERE hc.hypothesis_id = :hypothesis_id
                {condition}
                ORDER BY hc.revision DESC, hc.relevance_score DESC
                """
            ),
            {"hypothesis_id": hypothesis_id},
        )
    ).mappings().all()
    return [
        {
            "id": row["id"],
            "hypothesisId": row["hypothesis_id"],
            "revision": row["revision"],
            "cameraId": row["camera_id"],
            "name": row["name"],
            "sourceSystem": row["source_system"],
            "roadway": row["roadway"],
            "direction": row["direction"],
            "latitude": float(row["latitude"]),
            "longitude": float(row["longitude"]),
            "snapshotUrl": row["snapshot_url"],
            "streamUrl": row["stream_url"],
            "distanceMeters": round(float(row["distance_meters"]), 1),
            "roadwayMatch": bool(row["roadway_match"]),
            "directionMatch": bool(row["direction_match"]),
            "relevanceScore": round(float(row["relevance_score"]), 4),
            "preservationWindowStart": row["preservation_window_start"].isoformat(),
            "preservationWindowEnd": row["preservation_window_end"].isoformat(),
            "status": row["status"],
            "policy": {
                "causalRelationshipInferred": False,
                "partyAttributionInferred": False,
                "contactEligibilityEvaluated": False,
            },
        }
        for row in rows
    ]
