import { Router, Request, Response } from "express";
import { appendLedgerEntry } from "../ontology/ledger";

export type LegalAccessBasis =
  | "NotEstablished"
  | "PublicRecord"
  | "OpenRecordsRequest"
  | "ClientProvided"
  | "OtherLawfulBasis";

export type SolicitationReviewStatus =
  | "NotReviewed"
  | "WithinHoldPeriod"
  | "ClearedByCounsel"
  | "RejectedByCounsel";

export type ContactEligibilityStatus = "NotEvaluated" | "Ineligible" | "Eligible";
export type PartyStage = "UNKNOWN" | "CANDIDATE" | "CORROBORATED" | "VERIFIED";

export type PartyRole =
  | "Driver"
  | "Registered Owner"
  | "Motor Carrier"
  | "Witness"
  | "Injured Party";

export interface PartyRecord {
  id: string;
  subjectId: string;
  role: PartyRole;
  stage: PartyStage;
  note: string;
}

export interface ComplianceGateState {
  subjectId: string;
  legalAccessBasis: LegalAccessBasis;
  solicitationReviewStatus: SolicitationReviewStatus;
  solicitationHoldDays: number | null;
  suppressionChecked: boolean;
  contactEligibilityStatus: ContactEligibilityStatus;
  notes: string[];
  lastUpdated: string;
}

export interface ComplianceReviewInput {
  legalAccessBasis: LegalAccessBasis;
  solicitationReviewStatus: SolicitationReviewStatus;
  suppressionChecked: boolean;
  solicitationHoldDays?: number | null;
  note?: string;
  reviewer: string;
}

const GATES = new Map<string, ComplianceGateState>();
const PARTIES = new Map<string, PartyRecord>();

function defaultGate(subjectId: string): ComplianceGateState {
  return {
    subjectId,
    legalAccessBasis: "NotEstablished",
    solicitationReviewStatus: "NotReviewed",
    solicitationHoldDays: null,
    suppressionChecked: false,
    contactEligibilityStatus: "NotEvaluated",
    notes: [],
    lastUpdated: new Date().toISOString(),
  };
}

export function getOrCreateGate(subjectId: string): ComplianceGateState {
  let gate = GATES.get(subjectId);
  if (!gate) {
    gate = defaultGate(subjectId);
    GATES.set(subjectId, gate);
  }
  return gate;
}

export function evaluateContactEligibility(subjectId: string): ComplianceGateState {
  const gate = getOrCreateGate(subjectId);

  if (gate.legalAccessBasis === "NotEstablished") {
    gate.contactEligibilityStatus = "Ineligible";
    gate.notes.push("Blocked: no legal access basis established.");
  } else if (gate.solicitationReviewStatus !== "ClearedByCounsel") {
    gate.contactEligibilityStatus = "Ineligible";
    gate.notes.push(`Blocked: solicitation review status is '${gate.solicitationReviewStatus}'.`);
  } else if (!gate.suppressionChecked) {
    gate.contactEligibilityStatus = "Ineligible";
    gate.notes.push("Blocked: suppression/do-not-contact check not completed.");
  } else {
    gate.contactEligibilityStatus = "Eligible";
    gate.notes.push("All gates passed.");
  }

  gate.lastUpdated = new Date().toISOString();
  return gate;
}

export function applyComplianceReview(subjectId: string, input: ComplianceReviewInput): ComplianceGateState {
  const gate = getOrCreateGate(subjectId);
  gate.legalAccessBasis = input.legalAccessBasis;
  gate.solicitationReviewStatus = input.solicitationReviewStatus;
  gate.suppressionChecked = input.suppressionChecked;
  if (input.solicitationHoldDays !== undefined) gate.solicitationHoldDays = input.solicitationHoldDays;
  if (input.note) gate.notes.push(`[${input.reviewer}] ${input.note}`);

  const updated = evaluateContactEligibility(subjectId);

  appendLedgerEntry({
    entryType: "ComplianceDecision",
    subjectId,
    payload: {
      action: "compliance-review",
      reviewer: input.reviewer,
      inputs: {
        legalAccessBasis: input.legalAccessBasis,
        solicitationReviewStatus: input.solicitationReviewStatus,
        suppressionChecked: input.suppressionChecked,
        solicitationHoldDays: input.solicitationHoldDays ?? null,
      },
      resultingEligibility: updated.contactEligibilityStatus,
    },
    producedBy: `human:${input.reviewer}`,
    sourceSystem: "POST:/api/compliance/:subjectId/review",
  });

  return updated;
}

export interface ActivationResult {
  allowed: boolean;
  subjectId: string;
  status: string;
  reason?: string;
}

export function attemptActivation(subjectId: string, requestedBy: string): ActivationResult {
  const gate = getOrCreateGate(subjectId);
  const allowed = gate.contactEligibilityStatus === "Eligible";

  appendLedgerEntry({
    entryType: "ComplianceDecision",
    subjectId,
    payload: {
      action: "activation-attempt",
      requestedBy,
      allowed,
      gateStatusAtAttempt: gate.contactEligibilityStatus,
    },
    producedBy: `human:${requestedBy}`,
    sourceSystem: "POST:/api/compliance/:subjectId/activate",
  });

  if (!allowed) {
    return {
      allowed: false,
      subjectId,
      status: "BLOCKED",
      reason: `contactEligibilityStatus is '${gate.contactEligibilityStatus}'. Complete a compliance review first.`,
    };
  }

  return { allowed: true, subjectId, status: "ACTIVATED_FOR_ATTORNEY_OUTREACH" };
}

let partyCounter = 0;
const STAGE_ORDER: PartyStage[] = ["UNKNOWN", "CANDIDATE", "CORROBORATED", "VERIFIED"];

export function registerParty(
  subjectId: string,
  role: PartyRole,
  note: string,
  stage: PartyStage = "UNKNOWN"
): PartyRecord {
  partyCounter += 1;
  const party: PartyRecord = {
    id: `party_${String(partyCounter).padStart(4, "0")}`,
    subjectId,
    role,
    stage,
    note,
  };
  PARTIES.set(party.id, party);
  return party;
}

export function advancePartyStage(
  partyId: string,
  basisEvidenceIds: string[],
  advancedBy: string
): PartyRecord {
  const party = PARTIES.get(partyId);
  if (!party) throw new Error(`Unknown party: ${partyId}`);
  if (basisEvidenceIds.length === 0) {
    throw new Error("Stage advancement requires at least one evidence reference — unsupported jumps are not allowed.");
  }

  const idx = STAGE_ORDER.indexOf(party.stage);
  if (idx >= STAGE_ORDER.length - 1) throw new Error(`Party ${partyId} is already VERIFIED.`);
  party.stage = STAGE_ORDER[idx + 1];

  appendLedgerEntry({
    entryType: "ComplianceDecision",
    subjectId: party.subjectId,
    payload: {
      action: "party-stage-advance",
      partyId,
      newStage: party.stage,
      basisEvidenceIds,
    },
    producedBy: `human:${advancedBy}`,
    inputEntryIds: basisEvidenceIds,
  });

  return party;
}

export function partiesForSubject(subjectId: string): PartyRecord[] {
  return [...PARTIES.values()].filter((party) => party.subjectId === subjectId);
}

export const complianceRouter = Router();

// Register the more specific party route before subject-scoped routes.
complianceRouter.post("/parties/:partyId/advance", (req: Request, res: Response) => {
  const { basisEvidenceIds, advancedBy } = req.body ?? {};
  if (!advancedBy || !Array.isArray(basisEvidenceIds)) {
    return res.status(400).json({ error: "advancedBy and basisEvidenceIds (array) are required." });
  }

  try {
    return res.json(advancePartyStage(req.params.partyId, basisEvidenceIds, advancedBy));
  } catch (error) {
    return res.status(400).json({ error: error instanceof Error ? error.message : "Unknown error" });
  }
});

complianceRouter.get("/:subjectId/gate", (req: Request, res: Response) => {
  return res.json(getOrCreateGate(req.params.subjectId));
});

complianceRouter.post("/:subjectId/review", (req: Request, res: Response) => {
  const body = req.body ?? {};
  if (
    !body.reviewer ||
    !body.legalAccessBasis ||
    !body.solicitationReviewStatus ||
    typeof body.suppressionChecked !== "boolean"
  ) {
    return res.status(400).json({
      error: "reviewer, legalAccessBasis, solicitationReviewStatus, and suppressionChecked (boolean) are required.",
    });
  }

  return res.json(applyComplianceReview(req.params.subjectId, body as ComplianceReviewInput));
});

complianceRouter.post("/:subjectId/activate", (req: Request, res: Response) => {
  const requestedBy = req.body?.requestedBy;
  if (!requestedBy) {
    return res.status(400).json({ error: "requestedBy is required for the audit trail." });
  }

  const result = attemptActivation(req.params.subjectId, requestedBy);
  return res.status(result.allowed ? 200 : 403).json(result);
});

complianceRouter.post("/:subjectId/parties", (req: Request, res: Response) => {
  const { role, note, stage } = req.body ?? {};
  if (!role || !note) return res.status(400).json({ error: "role and note are required." });
  return res.json(registerParty(req.params.subjectId, role, note, stage ?? "UNKNOWN"));
});

complianceRouter.get("/:subjectId/parties", (req: Request, res: Response) => {
  return res.json(partiesForSubject(req.params.subjectId));
});
