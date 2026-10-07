import { createHash, randomUUID } from "crypto";

export type LedgerEntryType =
  | "Evidence" | "TemporalObservation" | "Assertion" | "Hypothesis"
  | "Score" | "Contradiction" | "HumanAdjudication" | "ComplianceDecision"
  | "Explanation" | "RagRetrieval";

export interface Provenance {
  producedBy: string;
  producedAt: string;
  inputEntryIds: string[];
  sourceSystem?: string;
  modelVersion?: string;
}

export interface LedgerEntry<T = unknown> {
  id: string;
  entryType: LedgerEntryType;
  subjectId: string;
  payload: Readonly<T>;
  provenance: Readonly<Provenance>;
  supersedesEntryId?: string;
  previousHash?: string;
  entryHash: string;
}

const ledger: LedgerEntry[] = [];

function canonical(value: unknown): string {
  if (Array.isArray(value)) return `[${value.map(canonical).join(",")}]`;
  if (value && typeof value === "object") {
    return `{${Object.entries(value as Record<string, unknown>).sort(([a],[b]) => a.localeCompare(b)).map(([k,v]) => `${JSON.stringify(k)}:${canonical(v)}`).join(",")}}`;
  }
  return JSON.stringify(value);
}

export function appendLedgerEntry<T>(args: {
  entryType: LedgerEntryType;
  subjectId: string;
  payload: T;
  producedBy: string;
  inputEntryIds?: string[];
  sourceSystem?: string;
  modelVersion?: string;
  supersedesEntryId?: string;
}): LedgerEntry<T> {
  const previousHash = ledger.at(-1)?.entryHash;
  const base = {
    id: randomUUID(), entryType: args.entryType, subjectId: args.subjectId,
    payload: structuredClone(args.payload),
    provenance: {
      producedBy: args.producedBy, producedAt: new Date().toISOString(),
      inputEntryIds: [...(args.inputEntryIds ?? [])], sourceSystem: args.sourceSystem,
      modelVersion: args.modelVersion
    },
    supersedesEntryId: args.supersedesEntryId, previousHash
  };
  const entryHash = createHash("sha256").update(canonical(base)).digest("hex");
  const entry = Object.freeze({ ...base, payload: Object.freeze(base.payload as object), provenance: Object.freeze(base.provenance), entryHash }) as LedgerEntry<T>;
  ledger.push(entry);
  return entry;
}

export function queryLedgerBySubject(subjectId: string, entryType?: LedgerEntryType): LedgerEntry[] {
  return ledger.filter(e => e.subjectId === subjectId && (!entryType || e.entryType === entryType));
}

export function fullProvenanceChain(entryId: string): LedgerEntry[] {
  const byId = new Map(ledger.map(e => [e.id, e]));
  const result: LedgerEntry[] = [], stack = [entryId], seen = new Set<string>();
  while (stack.length) {
    const id = stack.pop()!;
    if (seen.has(id)) continue;
    const entry = byId.get(id); if (!entry) continue;
    seen.add(id); result.push(entry); stack.push(...entry.provenance.inputEntryIds);
  }
  return result;
}

export function verifyLedgerIntegrity(): boolean {
  return ledger.every((entry, i) => i === 0 ? !entry.previousHash : entry.previousHash === ledger[i - 1].entryHash);
}
