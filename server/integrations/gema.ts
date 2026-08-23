import { FetchResult, NormalizedTrafficEvent, SourceDescriptor } from "./types";

export const GEMA_WAZE_SOURCE: SourceDescriptor = {
  id: "gema-waze-alerts",
  label: "GEMA Georgia Waze Alerts View",
  kind: "NEAR_REAL_TIME",
  access: "PUBLIC",
  enabled: true,
  authoritative: false,
  url: "https://services1.arcgis.com/2iUE8l8JKrP2tygQ/ArcGIS/rest/services/Georgia_Waze_Alerts_View/FeatureServer/0/query",
  note: "Public GEMA ArcGIS view of Waze-derived alerts; crowdsourced signal, not an authoritative crash report.",
};

function asText(value: unknown): string | undefined {
  return typeof value === "string" && value.trim() ? value.trim() : undefined;
}

function infer(description: string) {
  const s = description.toLowerCase();
  const fatalityHint = /fatal|death|deceased/.test(s);
  const injuryHint = fatalityHint || /injur|ambulance|ems|hospital/.test(s);
  const commercialVehicleHint = /tractor[- ]?trailer|semi\b|18[- ]?wheeler|commercial vehicle|box truck|dump truck|bus\b|truck\b/.test(s);
  const closureHint = /road closed|full closure|all lanes.*closed|blocked/.test(s);
  const stalledVehicleHint = /stopped|stall|disabled vehicle/.test(s);
  const debrisHint = /debris|object in road|wheel[- ]?off|tire in road/.test(s);
  const severityHint: NormalizedTrafficEvent["severityHint"] = fatalityHint ? "critical" : injuryHint || commercialVehicleHint || closureHint ? "high" : stalledVehicleHint || debrisHint ? "medium" : "low";
  return { fatalityHint, injuryHint, commercialVehicleHint, closureHint, stalledVehicleHint, debrisHint, severityHint };
}

export async function fetchGemaWazeAlerts(): Promise<FetchResult<NormalizedTrafficEvent>> {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), Number(process.env.GCCI_SOURCE_TIMEOUT_MS ?? 8000));
  try {
    const params = new URLSearchParams({ where: "1=1", outFields: "*", f: "geojson", outSR: "4326", returnGeometry: "true" });
    const response = await fetch(`${GEMA_WAZE_SOURCE.url}?${params.toString()}`, { signal: controller.signal, headers: { Accept: "application/geo+json, application/json" } });
    if (!response.ok) throw new Error(`HTTP ${response.status} ${response.statusText}`);
    const body: any = await response.json();
    const features = Array.isArray(body?.features) ? body.features : [];
    const records = features.map((feature: any): NormalizedTrafficEvent => {
      const p = feature.properties ?? {};
      const c = feature.geometry?.type === "Point" ? feature.geometry.coordinates : undefined;
      const description = asText(p.reportDescription ?? p.description ?? p.DESCRIPTION ?? p.subtype ?? p.type) ?? "Waze traffic alert";
      return {
        externalId: String(p.uuid ?? p.id ?? p.OBJECTID ?? feature.id ?? `${Date.now()}-${Math.random()}`),
        sourceId: GEMA_WAZE_SOURCE.id,
        sourceRecordType: "GemaWazeAlert",
        sourceUrl: GEMA_WAZE_SOURCE.url,
        observedAt: new Date().toISOString(),
        reportedAt: asText(p.pubMillis ?? p.reportedAt ?? p.starttime),
        updatedAt: asText(p.lastUpdated ?? p.updatedAt),
        roadway: asText(p.street ?? p.roadway ?? p.ROADWAY),
        direction: asText(p.direction ?? p.DIRECTION),
        locationText: asText(p.city ?? p.location ?? p.COUNTY_NAME),
        point: Array.isArray(c) && c.length >= 2 ? { longitude: Number(c[0]), latitude: Number(c[1]) } : undefined,
        eventType: asText(p.subtype ?? p.type ?? p.TYPE) ?? "WAZE_ALERT",
        description,
        ...infer(description),
        raw: feature,
      };
    });
    return { source: GEMA_WAZE_SOURCE, fetchedAt: new Date().toISOString(), records };
  } catch (error) {
    return { source: GEMA_WAZE_SOURCE, fetchedAt: new Date().toISOString(), records: [], error: error instanceof Error ? error.message : "Unknown source error" };
  } finally {
    clearTimeout(timer);
  }
}
