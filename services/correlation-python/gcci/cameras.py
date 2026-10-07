from __future__ import annotations

from .config import Settings, settings
from .models import Camera, CameraCandidate, IncidentHypothesis
from .utils import haversine_m, normalize_direction, normalize_roadway


def find_nearest_cameras(
    hypothesis: IncidentHypothesis,
    cameras: list[Camera],
    cfg: Settings = settings,
) -> list[CameraCandidate]:
    if not hypothesis.centroid:
        return []

    out: list[CameraCandidate] = []
    for camera in cameras:
        distance = haversine_m(
            hypothesis.centroid.latitude,
            hypothesis.centroid.longitude,
            camera.point.latitude,
            camera.point.longitude,
        )
        if distance > cfg.camera_search_radius_meters:
            continue

        roadway_match = bool(
            hypothesis.roadway
            and camera.roadway
            and normalize_roadway(hypothesis.roadway) == normalize_roadway(camera.roadway)
        )
        direction_match = bool(
            hypothesis.direction
            and camera.direction
            and normalize_direction(hypothesis.direction) == normalize_direction(camera.direction)
        )

        distance_score = max(0.0, 1.0 - distance / cfg.camera_search_radius_meters)
        relevance = min(
            1.0,
            0.70 * distance_score
            + 0.20 * (1.0 if roadway_match else 0.0)
            + 0.10 * (1.0 if direction_match else 0.0),
        )

        out.append(
            CameraCandidate(
                camera=camera,
                distance_meters=round(distance, 1),
                roadway_match=roadway_match,
                direction_match=direction_match,
                relevance_score=round(relevance, 4),
            )
        )

    out.sort(key=lambda x: x.relevance_score, reverse=True)
    return out[: cfg.max_camera_results]
