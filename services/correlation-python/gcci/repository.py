from __future__ import annotations

from datetime import timedelta
from uuid import uuid4

from geoalchemy2.elements import WKTElement
from sqlalchemy import and_, func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from .config import Settings, settings
from .database import EventRow, HypothesisEventRow, HypothesisRevisionRow, HypothesisRow, utcnow
from .models import GeoPoint, IncidentHypothesis, NormalizedEvent


def _point_wkt(point: GeoPoint | None) -> WKTElement | None:
    if point is None:
        return None
    return WKTElement(f"POINT({point.longitude} {point.latitude})", srid=4326)


def _event_time(event: NormalizedEvent):
    return event.reported_at or event.updated_at or event.observed_at


async def upsert_event(session: AsyncSession, event: NormalizedEvent) -> tuple[EventRow, bool]:
    now = utcnow()
    values = {
        "id": event.id,
        "source_kind": event.source_kind.value,
        "source_system": event.provenance.source_system,
        "source_record_id": event.provenance.source_record_id,
        "source_url": event.provenance.source_url,
        "raw_sha256": event.provenance.raw_sha256,
        "observed_at": event.observed_at,
        "reported_at": event.reported_at,
        "updated_at": event.updated_at,
        "geom": _point_wkt(event.point),
        "roadway": event.roadway,
        "direction": event.direction,
        "location_text": event.location_text,
        "event_type": event.event_type,
        "description": event.description,
        "lanes_affected": event.lanes_affected,
        "commercial_vehicle_hint": event.commercial_vehicle_hint,
        "injury_hint": event.injury_hint,
        "fatality_hint": event.fatality_hint,
        "closure_hint": event.closure_hint,
        "stalled_vehicle_hint": event.stalled_vehicle_hint,
        "debris_hint": event.debris_hint,
        "wheel_off_hint": event.wheel_off_hint,
        "attributes_json": event.attributes,
        "raw_json": event.raw,
        "last_ingested_at": now,
    }

    existing = await session.get(EventRow, event.id)
    is_new = existing is None

    stmt = insert(EventRow).values(first_ingested_at=now, **values)
    stmt = stmt.on_conflict_do_update(
        index_elements=[EventRow.id],
        set_={k: v for k, v in values.items() if k != "id"},
    ).returning(EventRow)
    row = (await session.execute(stmt)).scalar_one()
    return row, is_new


async def candidate_events_for(
    session: AsyncSession,
    event: NormalizedEvent,
    cfg: Settings = settings,
) -> list[EventRow]:
    center = _event_time(event)
    low = center - timedelta(seconds=cfg.candidate_time_window_seconds)
    high = center + timedelta(seconds=cfg.candidate_time_window_seconds)

    predicates = [
        EventRow.id != event.id,
        func.coalesce(EventRow.reported_at, EventRow.updated_at, EventRow.observed_at).between(low, high),
    ]

    if event.roadway:
        predicates.append(EventRow.roadway == event.roadway)

    if event.point:
        predicates.append(
            func.ST_DWithin(
                EventRow.geom,
                _point_wkt(event.point),
                cfg.candidate_radius_meters,
            )
        )

    rows = (
        await session.execute(select(EventRow).where(and_(*predicates)).limit(1000))
    ).scalars().all()
    return list(rows)


async def find_matching_hypothesis(
    session: AsyncSession,
    hypothesis: IncidentHypothesis,
    cfg: Settings = settings,
) -> HypothesisRow | None:
    predicates = [
        HypothesisRow.active.is_(True),
        HypothesisRow.end_time >= hypothesis.start_time - timedelta(seconds=cfg.candidate_time_window_seconds),
        HypothesisRow.start_time <= hypothesis.end_time + timedelta(seconds=cfg.candidate_time_window_seconds),
    ]

    if hypothesis.roadway:
        predicates.append(HypothesisRow.roadway == hypothesis.roadway)

    if hypothesis.centroid:
        predicates.append(
            func.ST_DWithin(
                HypothesisRow.centroid,
                _point_wkt(hypothesis.centroid),
                cfg.candidate_radius_meters,
            )
        )

    candidates = (
        await session.execute(
            select(HypothesisRow)
            .where(and_(*predicates))
            .order_by(HypothesisRow.updated_at.desc())
            .limit(25)
        )
    ).scalars().all()

    new_members = set(hypothesis.member_event_ids)
    for candidate in candidates:
        linked = (
            await session.execute(
                select(HypothesisEventRow.event_id).where(
                    HypothesisEventRow.hypothesis_id == candidate.id
                )
            )
        ).scalars().all()
        if new_members.intersection(linked):
            return candidate

    return candidates[0] if len(candidates) == 1 else None


async def persist_hypothesis_revision(
    session: AsyncSession,
    hypothesis: IncidentHypothesis,
) -> tuple[HypothesisRow, HypothesisRevisionRow, bool, list[str]]:
    current = await find_matching_hypothesis(session, hypothesis)
    created = current is None

    if current is None:
        current = HypothesisRow(
            id=f"inc_{uuid4().hex}",
            current_revision=0,
            active=True,
            start_time=hypothesis.start_time,
            end_time=hypothesis.end_time,
            centroid=_point_wkt(hypothesis.centroid),
            roadway=hypothesis.roadway,
            direction=hypothesis.direction,
        )
        session.add(current)
        await session.flush()

    existing_ids = set(
        (
            await session.execute(
                select(HypothesisEventRow.event_id).where(
                    HypothesisEventRow.hypothesis_id == current.id
                )
            )
        ).scalars().all()
    )
    all_member_ids = sorted(existing_ids.union(hypothesis.member_event_ids))
    newly_linked = sorted(set(hypothesis.member_event_ids) - existing_ids)

    revision_number = current.current_revision + 1
    current.current_revision = revision_number
    current.start_time = min(current.start_time, hypothesis.start_time)
    current.end_time = max(current.end_time, hypothesis.end_time)
    current.centroid = _point_wkt(hypothesis.centroid) if hypothesis.centroid else current.centroid
    current.roadway = hypothesis.roadway or current.roadway
    current.direction = hypothesis.direction or current.direction
    current.updated_at = utcnow()

    payload = hypothesis.model_dump(mode="json")
    payload["id"] = current.id
    payload["revision"] = revision_number
    payload["member_event_ids"] = all_member_ids

    revision = HypothesisRevisionRow(
        hypothesis_id=current.id,
        revision=revision_number,
        machine_confidence=hypothesis.machine_confidence,
        classification=hypothesis.classification.value,
        status=hypothesis.status.value,
        model_version=hypothesis.model_version,
        rationale_json=hypothesis.rationale,
        contradictions_json=hypothesis.contradictions,
        member_event_ids_json=all_member_ids,
        payload_json=payload,
    )
    session.add(revision)

    for event_id in newly_linked:
        session.add(
            HypothesisEventRow(
                hypothesis_id=current.id,
                event_id=event_id,
                first_linked_revision=revision_number,
            )
        )

    await session.flush()
    return current, revision, created, newly_linked
