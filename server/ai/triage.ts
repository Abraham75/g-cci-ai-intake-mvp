import { randomUUID } from "crypto";
import { scoreIntake } from "./scoring";
import { buildTemporalObservation, ONTOLOGY_VERSION } from "../ontology/model";
import { appendLedgerEntry } from "../ontology/ledger";

export function triageIntake(payload: any) {
  const intakeId = randomUUID();
  const temporal = buildTemporalObservation(payload);

  const evidenceEntry = appendLedgerEntry({
    entryType: "Evidence", subjectId: intakeId, payload,
    producedBy: "intake.triage", sourceSystem: "POST:/api/intake",
    modelVersion: ONTOLOGY_VERSION
  });
  const temporalEntry = appendLedgerEntry({
    entryType: "TemporalObservation", subjectId: intakeId, payload: temporal,
    producedBy: "intake.temporal-normalizer", inputEntryIds: [evidenceEntry.id],
    modelVersion: ONTOLOGY_VERSION
  });
  const scoring = scoreIntake(payload);
  const scoreEntry = appendLedgerEntry({
    entryType: "Score", subjectId: intakeId, payload: scoring,
    producedBy: "ai.scoreIntake", inputEntryIds: [evidenceEntry.id, temporalEntry.id],
    modelVersion: scoring.modelVersion
  });

  return {
    intakeId,
    receivedAt: temporal.ingestionTime,
    ontologyVersion: ONTOLOGY_VERSION,
    scoring,
    temporal,
    ledgerEntryId: scoreEntry.id,
    payload
  };
}
