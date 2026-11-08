from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import text

from .camera_repository import (
    camera_candidates_for_hypothesis,
    refresh_hypothesis_camera_candidates,
    upsert_camera_inventory,
)
from .database import SessionLocal
from .models import Camera


router = APIRouter(tags=["camera-intelligence"])


class CameraBatchRequest(BaseModel):
    cameras: list[Camera] = Field(min_length=1, max_length=10000)
    produced_by: str = "camera.api"


@router.post("/cameras/ingest-batch")
async def ingest_camera_batch(body: CameraBatchRequest) -> dict:
    """Upsert a durable camera inventory snapshot into PostgreSQL/PostGIS."""
    async with SessionLocal() as session:
        async with session.begin():
            count = await upsert_camera_inventory(
                session,
                body.cameras,
                produced_by=body.produced_by,
            )
    return {
        "upserted": count,
        "policy": {
            "cameraProximityImpliesCausation": False,
            "cameraProximityImpliesPartyAttribution": False,
            "contactEligibilityEvaluated": False,
        },
    }


@router.get("/cameras/status")
async def camera_inventory_status() -> dict:
    async with SessionLocal() as session:
        row = (
            await session.execute(
                text(
                    """
                    SELECT
                        count(*) FILTER (WHERE active = true) AS active_count,
                        count(*) AS total_count,
                        max(last_seen_at) AS last_seen_at
                    FROM traffic_cameras
                    """
                )
            )
        ).mappings().one()
    return {
        "activeCameraCount": int(row["active_count"] or 0),
        "totalCameraCount": int(row["total_count"] or 0),
        "lastSeenAt": row["last_seen_at"].isoformat() if row["last_seen_at"] else None,
    }


@router.get("/hypotheses/{hypothesis_id}/cameras")
async def hypothesis_cameras(
    hypothesis_id: str,
    current_only: bool = Query(default=True),
) -> list[dict]:
    async with SessionLocal() as session:
        rows = await camera_candidates_for_hypothesis(
            session,
            hypothesis_id,
            current_only=current_only,
        )
    return rows


@router.post("/hypotheses/{hypothesis_id}/cameras/refresh")
async def refresh_hypothesis_cameras(hypothesis_id: str) -> dict:
    """Recompute the candidate set from the current PostGIS camera inventory.

    Normally correlation refreshes the set automatically on every hypothesis
    revision. This endpoint is for inventory refreshes or explicit investigator
    re-evaluation when the hypothesis itself did not change.
    """
    try:
        async with SessionLocal() as session:
            async with session.begin():
                candidates = await refresh_hypothesis_camera_candidates(
                    session,
                    hypothesis_id,
                )
    except ValueError as exc:
        raise HTTPException(404, str(exc)) from exc

    return {
        "hypothesisId": hypothesis_id,
        "candidateCount": len(candidates),
        "candidates": [
            {
                **candidate,
                "preservationWindowStart": candidate["preservationWindowStart"].isoformat()
                if hasattr(candidate["preservationWindowStart"], "isoformat")
                else candidate["preservationWindowStart"],
                "preservationWindowEnd": candidate["preservationWindowEnd"].isoformat()
                if hasattr(candidate["preservationWindowEnd"], "isoformat")
                else candidate["preservationWindowEnd"],
            }
            for candidate in candidates
        ],
        "policy": {
            "scoreMeaning": "evidence-discovery relevance only",
            "causalRelationshipInferred": False,
            "partyAttributionInferred": False,
            "contactEligibilityEvaluated": False,
        },
    }
