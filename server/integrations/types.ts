export type SourceKind = "LIVE" | "NEAR_REAL_TIME" | "HISTORICAL" | "ENRICHMENT";
export type SourceAccess = "PUBLIC" | "API_KEY" | "PARTNER";

export interface SourceDescriptor {
  id: string;
  label: string;
  kind: SourceKind;
  access: SourceAccess;
  enabled: boolean;
  authoritative: boolean;
  url?: string;
  note?: string;
}

export interface GeoPoint {
  latitude: number;
  longitude: number;
}

export interface NormalizedTrafficEvent {
  externalId: string;
  sourceId: string;
  sourceRecordType: string;
  sourceUrl?: string;
  observedAt: string;
  reportedAt?: string;
  updatedAt?: string;
  roadway?: string;
  direction?: string;
  locationText?: string;
  point?: GeoPoint;
  eventType: string;
  severityHint?: "low" | "medium" | "high" | "critical";
  description?: string;
  lanesAffected?: string;
  commercialVehicleHint?: boolean;
  injuryHint?: boolean;
  fatalityHint?: boolean;
  closureHint?: boolean;
  stalledVehicleHint?: boolean;
  debrisHint?: boolean;
  raw: unknown;
}

export interface FetchResult<T> {
  source: SourceDescriptor;
  fetchedAt: string;
  records: T[];
  error?: string;
}
