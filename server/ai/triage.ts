import { randomUUID } from "crypto";
import { scoreIntake, ScoreIntakeInput } from "./scoring";
import {
  contradictionCountsFor,
  detectContradictions,
  EvidenceForDetection,
} from "./contradictions";
import { buildTemporalObservation, ONTOLOGY_VERSION } from "../ontology/model";
import { appendLedgerEntry, queryLedgerBySubject } from "../ontology/ledger";

function clamp01(value: unknown, fallback = 0): number {
  const n = typeof value === "number" ? value : Number(value);
  if (!Number.isFinite(n)) return fallback;
  return Math.max(0, Math.min(1, n));
}

function collectEvidenceForDetection(payload: any, ledgerEntryId: string): EvidenceForDetection[] {
  const evidence = Array.isArray(payload?.evidence) ? payload.evidence : [];

  return evidence.map((ev: any, index: number) => {
    const rawAttributes = ev?.attributes ?? ev?.observedAttributes ?? {};
    const attributes: Record<string, string> = {};

    if (rawAttributes && typeof rawAttributes === "object" && !Array.isArray(rawAttributes)) {
      for (const [key, value] of Object.entries(rawAttributes)) {
        if (value === null || value === undefined) continue;
        attributes[String(key)] = String(value);
      }
    }

    return {
      evidenceId: String(ev?.id ?? ev?.evidenceId ?? `evidence_${index + 1}`),
      ledgerEntryId,
      source: String(ev?.source ?? "intake_payload"),
      attributes,
    };
  });
}

function deriveScoreInput(payload: any, subjectId: string): ScoreIntakeInput {
  const evidence = Array.isArray(payload?.evidence) ? payload.evidence : [];
  const parties = Array.isArray(payload?.parties) ? payload.parties : [];
  const contradictions = contradictionCountsFor(subjectId);

  const numResolvedParties = parties.filter(
    (p: any) => p?.stage === "VERIFIED" || p?.identityStatus === "resolved_from_source",
  ).length;

  const severity = Number(payload?.preQual?.severity ?? payload?.injurySeverity ?? 0);
  const truckInvolved =
    payload?.preQual?.incidentType === "truck" ||
    payload?.truck_involved === true ||
    payload?.commercial_vehicle === true;

  const suppliedScores = payload?.scores ?? {};

  return {
    scores: {
      liability: clamp01(
        suppliedScores.liability ??
          (payload?.clear_liability === true ? 0.8 : payload?.liabilityScore),
        0.3,
      ),
      injury: clamp01(
        suppliedScores.injury ??
          (severity > 0 ? severity / 10 : payload?.injuryScore),
        0.2,
      ),
      collectability: clamp01(
        suppliedScores.collectability ??
          (truckInvolved ? 0.6 : payload?.collectabilityScore),
        0.2,
      ),
      evidence: clamp01(
        suppliedScores.evidence ??
          (evidence.length > 0 ? Math.min(1, evidence.length / 4) : payload?.evidenceScore),
        0.2,
      ),
      defendantResolution: clamp01(
        suppliedScores.defendantResolution ??
          (parties.length > 0 ? numResolvedParties / parties.length : payload?.defendantResolutionScore),
        0,
      ),
    },
    mechanism:
      payload?.mechanism ??
      payload?.incident?.mechanism ??
      payload?.incident?.type ??
      "UnknownIncident",
    evidenceCount: evidence.length,
    contradictions,
    numParties: parties.length,
    numResolvedParties,
  };
}

export function triageIntake(payload: any) {
  const intakeId = randomUUID();
  const temporal = buildTemporalObservation(payload);

  const evidenceEntry = appendLedgerEntry({
    entryType: "Evidence",
    subjectId: intakeId,
    payload,
    producedBy: "intake.triage",
    sourceSystem: "POST:/api/intake",
    modelVersion: ONTOLOGY_VERSION,
  });

  const temporalEntry = appendLedgerEntry({
    entryType: "TemporalObservation",
    subjectId: intakeId,
    payload: temporal,
    producedBy: "intake.temporal-normalizer",
    inputEntryIds: [evidenceEntry.id],
    modelVersion: ONTOLOGY_VERSION,
  });

  const evidenceForDetection = collectEvidenceForDetection(payload, evidenceEntry.id);
  const detectedContradictions = detectContradictions(intakeId, evidenceForDetection);

  const scoreInput = deriveScoreInput(payload, intakeId);
  const scoring = scoreIntake(scoreInput);
  const contradictionLedgerIds = queryLedgerBySubject(intakeId, "Contradiction").map((entry) => entry.id);

  const scoreEntry = appendLedgerEntry({
    entryType: "Score",
    subjectId: intakeId,
    payload: {
      input: scoreInput,
      result: scoring,
      detectedContradictions,
    },
    producedBy: "ai.scoreIntake",
    inputEntryIds: [evidenceEntry.id, temporalEntry.id, ...contradictionLedgerIds],
    modelVersion: scoring.modelVersion,
  });

  return {
    intakeId,
    receivedAt: temporal.ingestionTime,
    ontologyVersion: ONTOLOGY_VERSION,
    scoring,
    temporal,
    contradictions: detectedContradictions,
    ledgerEntryId: scoreEntry.id,
    payload,
  };
}
