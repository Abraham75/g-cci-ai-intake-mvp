export type FactStatus = "ObservedFact" | "InferredFact" | "Allegation" | "ModelPrediction" | "AttorneyValidatedFact";
export type AccessClassification = "OpenPublicData" | "OpenRecordsRequestRequired" | "RestrictedGovernmentData" | "DPPARestricted" | "HIPAARestricted" | "DiscoveryObtainable" | "SubpoenaRequired" | "CourtOrderRequired" | "Unclassified";

export interface TemporalObservation {
  eventOccurrenceTime?: string;
  firstCallTime?: string;
  cadCreationTime?: string;
  firstDetectionTime?: string;
  unitArrivalTime?: string;
  recordCreationTime?: string;
  sourceTime?: string;
  ingestionTime: string;
  effectiveTime?: string;
  clockUncertaintySeconds?: number;
}

export interface ConfidenceBreakdown {
  eventCorrelation: number;
  causalRelationship: number;
  partyAttribution: number;
}

export interface CaseOpportunityScore {
  score: number;
  tier: "HIGH" | "MEDIUM" | "LOW";
  reasons: string[];
  reviewedAt: string;
  confidence: ConfidenceBreakdown;
  modelVersion: string;
}

export const ONTOLOGY_VERSION = "gcci-ontology-v1.0.0";
export const SCORING_MODEL_VERSION = "gcci-intake-score-v1.0.0";

export function buildTemporalObservation(payload: any): TemporalObservation {
  const incidentTime = payload?.incident?.occurredAt ?? payload?.incident?.dateTime;
  return {
    eventOccurrenceTime: incidentTime,
    firstCallTime: payload?.incident?.firstCallTime,
    cadCreationTime: payload?.incident?.cadCreationTime,
    firstDetectionTime: payload?.incident?.firstDetectionTime,
    unitArrivalTime: payload?.incident?.unitArrivalTime,
    recordCreationTime: payload?.incident?.recordCreationTime,
    sourceTime: payload?.source?.sourceTime,
    ingestionTime: new Date().toISOString(),
    effectiveTime: payload?.source?.effectiveTime,
    clockUncertaintySeconds: payload?.source?.clockUncertaintySeconds
  };
}
