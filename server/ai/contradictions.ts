import { Router, Request, Response } from "express";
import { appendLedgerEntry } from "../ontology/ledger";

export type ContradictionSeverity = "high" | "medium" | "low";

export interface EvidenceForDetection {
  evidenceId: string;
  ledgerEntryId?: string;
  source: string;
  attributes: Record<string, string>;
}

export interface ConflictingValue {
  value: string;
  evidenceId: string;
  source: string;
}

export interface ContradictionRecord {
  id: string;
  subjectId: string;
  attributeKey: string;
  values: ConflictingValue[];
  severity: ContradictionSeverity;
  detectedAt: string;
  resolved: boolean;
  resolution?: {
    resolvedBy: string;
    acceptedValue: string;
    basisEvidenceIds: string[];
    note?: string;
    resolvedAt: string;
  };
}

export const SEVERITY_RULES: Record<string, ContradictionSeverity> = {
  vehicle_color: "high",
  vehicle_type: "high",
  license_plate: "high",
  carrier_name: "high",
  incident_time: "medium",
  travel_direction: "medium",
  lane: "medium",
  weather: "low",
  road_condition: "low",
};

export const DEFAULT_SEVERITY: ContradictionSeverity = "medium";

export function severityFor(attributeKey: string): ContradictionSeverity {
  return SEVERITY_RULES[attributeKey] ?? DEFAULT_SEVERITY;
}

const CONTRADICTIONS = new Map<string, ContradictionRecord>();
let contradictionCounter = 0;

function nextId(): string {
  contradictionCounter += 1;
  return `con_${String(contradictionCounter).padStart(4, "0")}`;
}

export function contradictionsForSubject(subjectId: string): ContradictionRecord[] {
  return [...CONTRADICTIONS.values()].filter((c) => c.subjectId === subjectId);
}

export function detectContradictions(subjectId: string, evidence: EvidenceForDetection[]): ContradictionRecord[] {
  const byKey = new Map<string, Map<string, ConflictingValue>>();

  for (const ev of evidence) {
    for (const [key, value] of Object.entries(ev.attributes ?? {})) {
      let values = byKey.get(key);
      if (!values) {
        values = new Map();
        byKey.set(key, values);
      }
      if (!values.has(value)) {
        values.set(value, { value, evidenceId: ev.evidenceId, source: ev.source });
      }
    }
  }

  const results: ContradictionRecord[] = [];

  for (const [attributeKey, values] of byKey.entries()) {
    if (values.size < 2) continue;

    const existing = [...CONTRADICTIONS.values()].find(
      (c) => c.subjectId === subjectId && c.attributeKey === attributeKey && !c.resolved,
    );

    if (existing) {
      const known = new Set(existing.values.map((v) => v.value));
      for (const v of values.values()) {
        if (!known.has(v.value)) existing.values.push(v);
      }
      results.push(existing);
      continue;
    }

    const record: ContradictionRecord = {
      id: nextId(),
      subjectId,
      attributeKey,
      values: [...values.values()],
      severity: severityFor(attributeKey),
      detectedAt: new Date().toISOString(),
      resolved: false,
    };
    CONTRADICTIONS.set(record.id, record);

    appendLedgerEntry({
      entryType: "Contradiction",
      subjectId,
      payload: {
        action: "contradiction-detected",
        contradictionId: record.id,
        attributeKey,
        conflictingValues: record.values,
        severity: record.severity,
      },
      producedBy: "ai.contradictionEngine",
      inputEntryIds: evidence.map((e) => e.ledgerEntryId).filter((id): id is string => !!id),
    });

    results.push(record);
  }

  return results;
}

export function resolveContradiction(
  contradictionId: string,
  resolvedBy: string,
  acceptedValue: string,
  basisEvidenceIds: string[],
  note?: string,
): ContradictionRecord {
  const record = CONTRADICTIONS.get(contradictionId);
  if (!record) throw new Error(`Unknown contradiction: ${contradictionId}`);
  if (record.resolved) throw new Error(`Contradiction ${contradictionId} is already resolved.`);
  if (basisEvidenceIds.length === 0) {
    throw new Error("Resolution requires at least one evidence reference — unsupported dismissals are not allowed.");
  }
  if (!record.values.some((v) => v.value === acceptedValue)) {
    throw new Error(
      `acceptedValue '${acceptedValue}' is not among the conflicting values — a resolution must pick one of the actually-asserted values or new evidence must be attached first.`,
    );
  }

  record.resolved = true;
  record.resolution = {
    resolvedBy,
    acceptedValue,
    basisEvidenceIds,
    note,
    resolvedAt: new Date().toISOString(),
  };

  appendLedgerEntry({
    entryType: "Contradiction",
    subjectId: record.subjectId,
    payload: {
      action: "contradiction-resolved",
      contradictionId,
      acceptedValue,
      basisEvidenceIds,
      note: note ?? null,
    },
    producedBy: `human:${resolvedBy}`,
    inputEntryIds: basisEvidenceIds,
  });

  return record;
}

export function contradictionCountsFor(subjectId: string): { highSeverityUnresolved: number; other: number } {
  let highSeverityUnresolved = 0;
  let other = 0;
  for (const c of CONTRADICTIONS.values()) {
    if (c.subjectId !== subjectId) continue;
    if (c.severity === "high" && !c.resolved) highSeverityUnresolved += 1;
    else other += 1;
  }
  return { highSeverityUnresolved, other };
}

export const contradictionsRouter = Router();

contradictionsRouter.post("/:contradictionId/resolve", (req: Request, res: Response) => {
  const { resolvedBy, acceptedValue, basisEvidenceIds, note } = req.body ?? {};
  if (!resolvedBy || !acceptedValue || !Array.isArray(basisEvidenceIds)) {
    return res.status(400).json({ error: "resolvedBy, acceptedValue, and basisEvidenceIds (array) are required." });
  }
  try {
    return res.json(resolveContradiction(req.params.contradictionId, resolvedBy, acceptedValue, basisEvidenceIds, note));
  } catch (err) {
    return res.status(400).json({ error: err instanceof Error ? err.message : "Unknown error" });
  }
});

contradictionsRouter.get("/subject/:subjectId", (req: Request, res: Response) => {
  return res.json(contradictionsForSubject(req.params.subjectId));
});

contradictionsRouter.post("/subject/:subjectId/detect", (req: Request, res: Response) => {
  const evidence = req.body?.evidence;
  if (!Array.isArray(evidence)) {
    return res.status(400).json({ error: "evidence (array of {evidenceId, source, attributes}) is required." });
  }
  return res.json(detectContradictions(req.params.subjectId, evidence as EvidenceForDetection[]));
});

contradictionsRouter.get("/subject/:subjectId/counts", (req: Request, res: Response) => {
  return res.json(contradictionCountsFor(req.params.subjectId));
});
