from __future__ import annotations

from .cameras import find_nearest_cameras
from .config import Settings, settings
from .correlation import build_incident_hypotheses
from .evidence_gaps import rank_evidence_gaps
from .models import Camera, CorrelatedIncidentPackage, NormalizedEvent


class CrossSourceCorrelationService:
    def __init__(self, cfg: Settings = settings):
        self.cfg = cfg

    def analyze(self, events: list[NormalizedEvent], cameras: list[Camera]) -> list[CorrelatedIncidentPackage]:
        hypotheses, correlations = build_incident_hypotheses(events, self.cfg)
        by_id = {e.id: e for e in events}
        packages: list[CorrelatedIncidentPackage] = []

        for hypothesis in hypotheses:
            cluster_events = [by_id[eid] for eid in hypothesis.member_event_ids]
            member_ids = set(hypothesis.member_event_ids)
            internal_correlations = [
                c for c in correlations
                if c.event_a_id in member_ids and c.event_b_id in member_ids
            ]
            nearest = find_nearest_cameras(hypothesis, cameras, self.cfg)
            gaps = rank_evidence_gaps(hypothesis, cluster_events, nearest, self.cfg)
            packages.append(
                CorrelatedIncidentPackage(
                    hypothesis=hypothesis,
                    events=cluster_events,
                    pairwise_correlations=internal_correlations,
                    nearest_cameras=nearest,
                    evidence_gaps=gaps,
                    causal_relationship_confidence=None,
                    party_attribution_confidence=None,
                    contact_eligibility="NOT_EVALUATED",
                )
            )
        return packages
