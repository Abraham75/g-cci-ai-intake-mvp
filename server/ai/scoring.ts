import {
  CaseOpportunityScore,
  ConfidenceBreakdown,
  ScoreComponents,
  SCORING_MODEL_VERSION,
  Tier,
} from "../ontology/model";

export interface ScoreIntakeInput {
  scores: Omit<ScoreComponents, "mechanismSeverity" | "uncertaintyPenalty">;
  mechanism: string;
  evidenceCount: number;
  contradictions: {
    highSeverityUnresolved: number;
    other: number;
  };
  numParties: number;
  numResolvedParties: number;
}

export const MECHANISM_SEVERITY: Record<string, number> = {
  WheelOffIncident: 0.9,
  MechanicalFailureIncident: 0.75,
  AngleCollision: 0.65,
  SideswipeCollision: 0.6,
  DebrisIncident: 0.55,
  RearEndCollision: 0.5,
  VehicleStall: 0.3,
};

export function computeCaseOpportunityScore(s: ScoreComponents): number {
  const raw =
    0.25 * s.liability +
    0.20 * s.injury +
    0.20 * s.collectability +
    0.15 * s.evidence +
    0.10 * s.mechanismSeverity +
    0.10 * s.defendantResolution -
    0.20 * s.uncertaintyPenalty;
  return Math.max(0, Math.min(1, raw));
}

export function classifyTier(cos: number, hasUnresolvedHighSeverityContradiction: boolean): Tier {
  if (hasUnresolvedHighSeverityContradiction) return "C";
  if (cos >= 0.80) return "A";
  if (cos >= 0.65) return "B";
  if (cos >= 0.45) return "C";
  return "D";
}

export function computeUncertaintyPenalty(
  numHighSeverityUnresolved: number,
  numOther: number = 0,
): number {
  const penalty = 0.22 * numHighSeverityUnresolved + 0.05 * numOther;
  return Math.min(1, Math.round(penalty * 100) / 100);
}

export function computeEventCorrelation(evidenceCount: number): number {
  return Math.round(Math.min(1, 0.5 + 0.25 * evidenceCount) * 100) / 100;
}

export function computeCausalRelationship(
  eventCorrelation: number,
  hasAnyContradiction: boolean,
): number {
  const factor = hasAnyContradiction ? 0.6 : 0.9;
  return Math.round(eventCorrelation * factor * 100) / 100;
}

export function computePartyAttribution(numParties: number, numResolved: number): number {
  if (numParties === 0) return 0;
  return Math.round(0.5 * (numResolved / numParties) * 100) / 100;
}

export function computeConfidenceDimensions(
  evidenceCount: number,
  hasAnyContradiction: boolean,
  numParties: number,
  numResolved: number,
): ConfidenceBreakdown {
  const eventCorrelation = computeEventCorrelation(evidenceCount);
  return {
    eventCorrelation,
    causalRelationship: computeCausalRelationship(eventCorrelation, hasAnyContradiction),
    partyAttribution: computePartyAttribution(numParties, numResolved),
  };
}

export function mechanismSeverityFor(mechanism: string): number {
  return MECHANISM_SEVERITY[mechanism] ?? 0.4;
}

export function scoreIntake(input: ScoreIntakeInput): CaseOpportunityScore {
  const uncertaintyPenalty = computeUncertaintyPenalty(
    input.contradictions.highSeverityUnresolved,
    input.contradictions.other,
  );

  const scores: ScoreComponents = {
    ...input.scores,
    mechanismSeverity: mechanismSeverityFor(input.mechanism),
    uncertaintyPenalty,
  };

  const cos = computeCaseOpportunityScore(scores);
  const hasUnresolvedHighSeverity = input.contradictions.highSeverityUnresolved > 0;
  const tier = classifyTier(cos, hasUnresolvedHighSeverity);
  const confidence = computeConfidenceDimensions(
    input.evidenceCount,
    input.contradictions.highSeverityUnresolved + input.contradictions.other > 0,
    input.numParties,
    input.numResolvedParties,
  );

  const reasons: string[] = [];
  if (scores.liability > 0.5) reasons.push("Meaningful liability signal present");
  if (scores.injury > 0.3) reasons.push("Meaningful injury signal present");
  if (scores.collectability > 0.5) reasons.push("Commercial/collectable defendant likely");
  if (hasUnresolvedHighSeverity) reasons.push("Unresolved high-severity contradiction — forced to Tier C");

  return {
    score: Math.round(cos * 100) / 100,
    tier,
    reasons,
    confidence,
    modelVersion: SCORING_MODEL_VERSION,
    reviewedAt: new Date().toISOString(),
  };
}
