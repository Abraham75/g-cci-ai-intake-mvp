import { CaseOpportunityScore, SCORING_MODEL_VERSION } from "../ontology/model";

export function scoreIntake(intake: any): CaseOpportunityScore {
  let score = 0;
  const reasons: string[] = [];

  if (intake?.preQual?.incidentType === "truck") {
    score += 30;
    reasons.push("Commercial vehicle involved");
  }
  if (intake?.preQual?.severity >= 7) {
    score += 25;
    reasons.push("Severe injury");
  }
  if (intake?.incident?.description?.length > 200) {
    score += 15;
    reasons.push("Detailed incident narrative");
  }
  if (intake?.claimant?.email && intake?.claimant?.phone) {
    score += 10;
    reasons.push("Complete contact information");
  }

  const tier = score >= 60 ? "HIGH" : score >= 35 ? "MEDIUM" : "LOW";

  // These measures are intentionally independent. In particular, contact
  // completeness and case-opportunity scoring never increase attribution.
  const evidenceCount = Array.isArray(intake?.evidence) ? intake.evidence.length : 0;
  const eventCorrelation = Math.min(1, 0.25 + evidenceCount * 0.15);
  const causalRelationship = Math.min(1, (intake?.preQual?.severity ?? 0) / 10 * 0.5);
  const partyAttribution = intake?.defendant?.identityVerified === true ? 0.75 : 0;

  return {
    score, tier, reasons,
    reviewedAt: new Date().toISOString(),
    confidence: { eventCorrelation, causalRelationship, partyAttribution },
    modelVersion: SCORING_MODEL_VERSION
  };
}
