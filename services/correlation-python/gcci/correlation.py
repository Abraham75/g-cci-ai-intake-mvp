from __future__ import annotations

from datetime import datetime
from itertools import combinations
from statistics import mean
from typing import Iterable
from uuid import uuid4

from .config import Settings, settings
from .models import CorrelationClass, FactorScore, GeoPoint, IncidentHypothesis, NormalizedEvent, PairCorrelation
from .utils import haversine_m, jaccard, normalize_direction, normalize_roadway, token_set


def _event_time(event: NormalizedEvent) -> datetime:
    return event.reported_at or event.updated_at or event.observed_at


def temporal_score(a: NormalizedEvent, b: NormalizedEvent, window_seconds: int) -> FactorScore:
    delta = abs((_event_time(a) - _event_time(b)).total_seconds())
    score = max(0.0, 1.0 - delta / window_seconds)
    return FactorScore(factor="temporal", score=round(score, 4), reason=f"Event timestamps differ by {delta:.0f} seconds.")


def spatial_score(a: NormalizedEvent, b: NormalizedEvent, radius_meters: float) -> FactorScore:
    if not a.point or not b.point:
        return FactorScore(factor="spatial", score=0.25, reason="One or both events lack precise coordinates; weak spatial prior applied.")
    distance = haversine_m(a.point.latitude, a.point.longitude, b.point.latitude, b.point.longitude)
    score = max(0.0, 1.0 - distance / radius_meters)
    return FactorScore(factor="spatial", score=round(score, 4), reason=f"Events are approximately {distance:.0f} meters apart.")


def roadway_score(a: NormalizedEvent, b: NormalizedEvent) -> FactorScore:
    ra, rb = normalize_roadway(a.roadway), normalize_roadway(b.roadway)
    if ra and rb and ra == rb:
        return FactorScore(factor="roadway", score=1.0, reason=f"Both resolve to roadway {ra}.")
    similarity = jaccard(token_set(ra), token_set(rb))
    return FactorScore(factor="roadway", score=round(similarity, 4), reason=f"Roadway token similarity is {similarity:.2f}.")


def direction_score(a: NormalizedEvent, b: NormalizedEvent) -> tuple[FactorScore, list[str]]:
    da, db = normalize_direction(a.direction), normalize_direction(b.direction)
    if not da or not db:
        return FactorScore(factor="direction", score=0.5, reason="Direction is missing from at least one source."), []
    if da == db:
        return FactorScore(factor="direction", score=1.0, reason=f"Both events are {da}."), []
    return FactorScore(factor="direction", score=0.0, reason=f"Direction conflict: {da} vs {db}."), [f"Travel-direction conflict: {a.id}={da}, {b.id}={db}"]


def mechanism_score(a: NormalizedEvent, b: NormalizedEvent) -> FactorScore:
    def signals(e: NormalizedEvent) -> set[str]:
        return {
            "commercial_vehicle" if e.commercial_vehicle_hint else "",
            "injury" if e.injury_hint else "",
            "fatality" if e.fatality_hint else "",
            "closure" if e.closure_hint else "",
            "stall" if e.stalled_vehicle_hint else "",
            "debris" if e.debris_hint else "",
            "wheel_off" if e.wheel_off_hint else "",
        } - {""}

    sa, sb = signals(a), signals(b)
    structured = jaccard(sa, sb)
    text_similarity = jaccard(token_set(a.description), token_set(b.description))
    score = max(structured, 0.6 * structured + 0.4 * text_similarity)
    return FactorScore(factor="mechanism", score=round(score, 4), reason=f"Mechanism/text semantic-overlap score is {score:.2f}.")


def corroboration_score(a: NormalizedEvent, b: NormalizedEvent) -> FactorScore:
    independent = a.provenance.source_system != b.provenance.source_system
    return FactorScore(
        factor="corroboration",
        score=1.0 if independent else 0.35,
        reason="Independent source systems provide corroboration." if independent else "Both records originate from the same source system.",
    )


def correlate_pair(a: NormalizedEvent, b: NormalizedEvent, cfg: Settings = settings) -> PairCorrelation:
    factors = [
        temporal_score(a, b, cfg.candidate_time_window_seconds),
        spatial_score(a, b, cfg.candidate_radius_meters),
        roadway_score(a, b),
        mechanism_score(a, b),
        corroboration_score(a, b),
    ]
    direction_factor, contradictions = direction_score(a, b)
    factors.insert(3, direction_factor)
    f = {x.factor: x.score for x in factors}
    w = cfg.weights
    score = (
        w.temporal * f["temporal"]
        + w.spatial * f["spatial"]
        + w.roadway * f["roadway"]
        + w.direction * f["direction"]
        + w.mechanism * f["mechanism"]
        + w.corroboration * f["corroboration"]
    )
    if score >= cfg.same_incident_threshold:
        classification = CorrelationClass.SAME_INCIDENT
    elif score >= cfg.related_incident_threshold:
        classification = CorrelationClass.RELATED_INCIDENT
    elif score >= 0.40:
        classification = CorrelationClass.POSSIBLE_CONNECTION
    else:
        classification = CorrelationClass.UNRELATED
    return PairCorrelation(event_a_id=a.id, event_b_id=b.id, score=round(score, 4), classification=classification, factors=factors, contradictions=contradictions)


def _candidate_pair(a: NormalizedEvent, b: NormalizedEvent, cfg: Settings) -> bool:
    if abs((_event_time(a) - _event_time(b)).total_seconds()) > cfg.candidate_time_window_seconds:
        return False
    if a.point and b.point:
        distance = haversine_m(a.point.latitude, a.point.longitude, b.point.latitude, b.point.longitude)
        if distance > cfg.candidate_radius_meters:
            return False
    ra, rb = normalize_roadway(a.roadway), normalize_roadway(b.roadway)
    if ra and rb and ra != rb and not (token_set(ra) & token_set(rb)):
        return False
    return True


class UnionFind:
    def __init__(self, ids: Iterable[str]):
        self.parent = {x: x for x in ids}

    def find(self, x: str) -> str:
        while self.parent[x] != x:
            self.parent[x] = self.parent[self.parent[x]]
            x = self.parent[x]
        return x

    def union(self, a: str, b: str) -> None:
        ra, rb = self.find(a), self.find(b)
        if ra != rb:
            self.parent[rb] = ra


def build_incident_hypotheses(events: list[NormalizedEvent], cfg: Settings = settings) -> tuple[list[IncidentHypothesis], list[PairCorrelation]]:
    by_id = {e.id: e for e in events}
    uf = UnionFind(by_id)
    correlations: list[PairCorrelation] = []

    for a, b in combinations(events, 2):
        if not _candidate_pair(a, b, cfg):
            continue
        result = correlate_pair(a, b, cfg)
        correlations.append(result)
        if result.classification in {CorrelationClass.SAME_INCIDENT, CorrelationClass.RELATED_INCIDENT}:
            uf.union(a.id, b.id)

    groups: dict[str, list[NormalizedEvent]] = {}
    for event in events:
        groups.setdefault(uf.find(event.id), []).append(event)

    hypotheses: list[IncidentHypothesis] = []
    for members in groups.values():
        member_ids = {e.id for e in members}
        internal = [c for c in correlations if c.event_a_id in member_ids and c.event_b_id in member_ids]
        confidence = mean([c.score for c in internal]) if internal else 0.50
        if internal and all(c.classification == CorrelationClass.SAME_INCIDENT for c in internal):
            classification = CorrelationClass.SAME_INCIDENT
        elif internal:
            classification = CorrelationClass.RELATED_INCIDENT
        else:
            classification = CorrelationClass.POSSIBLE_CONNECTION

        points = [e.point for e in members if e.point]
        centroid = GeoPoint(latitude=mean([p.latitude for p in points]), longitude=mean([p.longitude for p in points])) if points else None
        times = [_event_time(e) for e in members]

        def mode_or_none(values: list[str | None]) -> str | None:
            vals = [v for v in values if v]
            return max(set(vals), key=vals.count) if vals else None

        contradictions = sorted({x for c in internal for x in c.contradictions})
        rationale = [
            f"{len(members)} source record(s) grouped.",
            f"{len(set(e.provenance.source_system for e in members))} independent source system(s).",
        ]
        if internal:
            rationale.append(f"Mean internal correlation score: {confidence:.2f}.")

        hypotheses.append(IncidentHypothesis(
            id=f"hyp_{uuid4().hex[:12]}",
            member_event_ids=sorted(member_ids),
            machine_confidence=round(confidence, 4),
            classification=classification,
            rationale=rationale,
            contradictions=contradictions,
            centroid=centroid,
            start_time=min(times),
            end_time=max(times),
            roadway=mode_or_none([normalize_roadway(e.roadway) for e in members]),
            direction=mode_or_none([normalize_direction(e.direction) for e in members]),
        ))

    hypotheses.sort(key=lambda h: h.machine_confidence, reverse=True)
    correlations.sort(key=lambda c: c.score, reverse=True)
    return hypotheses, correlations
