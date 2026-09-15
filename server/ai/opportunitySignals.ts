import { appendLedgerEntry } from "../ontology/ledger";
import { NormalizedTrafficEvent } from "../integrations/types";

export interface OpportunitySignal {
  id: string;
  eventKey: string;
  score: number;
  tier: "A" | "B" | "C" | "D";
  reasons: string[];
  recommendedEvidence: string[];
  event: Omit<NormalizedTrafficEvent, "raw">;
  outreachPermitted: false;
  generatedAt: string;
  modelVersion: string;
}

export const SIGNAL_MODEL_VERSION = "gcci-public-incident-signal-v1.0";

function clamp01(v: number): number { return Math.max(0, Math.min(1, v)); }

function eventStrength(event: NormalizedTrafficEvent): { score: number; reasons: string[]; evidence: string[] } {
  let score = 0.10;
  const reasons: string[] = [];
  const evidence = new Set<string>(["Crash/incident report", "911/CAD record"]);

  if (event.commercialVehicleHint) {
    score += 0.22;
    reasons.push("Commercial-vehicle involvement signal");
    evidence.add("FMCSA carrier/vehicle enrichment");
    evidence.add("ELD/telematics preservation request");
  }
  if (event.fatalityHint) {
    score += 0.30;
    reasons.push("Fatality-language signal");
    evidence.add("Medical examiner/coroner record where lawfully accessible");
  } else if (event.injuryHint) {
    score += 0.20;
    reasons.push("Injury/EMS language signal");
  }
  if (event.closureHint) {
    score += 0.12;
    reasons.push("Major roadway disruption/full-closure signal");
    evidence.add("Traffic management/CCTV preservation");
  }
  if (event.debrisHint) {
    score += 0.12;
    reasons.push("Debris/wheel-off roadway hazard signal");
    evidence.add("Tow/recovery records");
    evidence.add("Maintenance/inspection records if a CMV is later corroborated");
  }
  if (event.stalledVehicleHint) {
    score += 0.05;
    reasons.push("Disabled/stalled vehicle signal");
    evidence.add("Tow dispatch record");
  }
  if (event.severityHint === "critical") score += 0.10;
  else if (event.severityHint === "high") score += 0.06;

  if (event.point) {
    score += 0.04;
    reasons.push("Precise geospatial location available for cross-source correlation");
    evidence.add("Nearby traffic-camera snapshots/video");
  }

  return { score: clamp01(score), reasons, evidence: [...evidence] };
}

function classify(score: number): "A" | "B" | "C" | "D" {
  if (score >= 0.80) return "A";
  if (score >= 0.65) return "B";
  if (score >= 0.45) return "C";
  return "D";
}

function stableEventKey(event: NormalizedTrafficEvent): string {
  return `${event.sourceId}:${event.externalId}`;
}

export function synthesizeOpportunitySignals(events: NormalizedTrafficEvent[]): OpportunitySignal[] {
  const deduped = new Map<string, NormalizedTrafficEvent>();
  for (const event of events) deduped.set(stableEventKey(event), event);

  return [...deduped.values()]
    .map((event) => {
      const derived = eventStrength(event);
      const { raw: _raw, ...safeEvent } = event;
      const signal: OpportunitySignal = {
        id: `signal:${stableEventKey(event)}`,
        eventKey: stableEventKey(event),
        score: Math.round(derived.score * 100) / 100,
        tier: classify(derived.score),
        reasons: derived.reasons,
        recommendedEvidence: derived.evidence,
        event: safeEvent,
        outreachPermitted: false,
        generatedAt: new Date().toISOString(),
        modelVersion: SIGNAL_MODEL_VERSION,
      };
      return signal;
    })
    .sort((a, b) => b.score - a.score);
}

export function ledgerOpportunitySignals(signals: OpportunitySignal[]): void {
  for (const signal of signals) {
    appendLedgerEntry({
      entryType: "Assertion",
      subjectId: signal.eventKey,
      payload: {
        assertionType: "PublicIncidentOpportunitySignal",
        signal,
        complianceBoundary: "INCIDENT_SIGNAL_ONLY_NO_PERSON_IDENTIFICATION_OR_OUTREACH_AUTHORIZATION",
      },
      producedBy: "ai.opportunitySignals",
      sourceSystem: signal.event.sourceId,
      modelVersion: SIGNAL_MODEL_VERSION,
    });
  }
}
