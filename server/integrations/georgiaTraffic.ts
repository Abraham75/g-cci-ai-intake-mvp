import { FetchResult, NormalizedTrafficEvent, SourceDescriptor } from "./types";

const TIMEOUT_MS = Number(process.env.GCCI_SOURCE_TIMEOUT_MS ?? 8000);

export const SOURCE_CATALOG: SourceDescriptor[] = [
  { id: "gdoti511-events", label: "GDOT 511 Events", kind: "LIVE", access: "API_KEY", enabled: Boolean(process.env.GDOT_511_API_KEY), authoritative: true, url: "https://511ga.org/api/v2/get/event" },
  { id: "gdoti511-alerts", label: "GDOT 511 Alerts", kind: "LIVE", access: "API_KEY", enabled: Boolean(process.env.GDOT_511_API_KEY), authoritative: true, url: "https://511ga.org/api/v2/get/alerts" },
  { id: "gdoti511-cameras", label: "GDOT 511 Cameras", kind: "LIVE", access: "API_KEY", enabled: Boolean(process.env.GDOT_511_API_KEY), authoritative: true, url: "https://511ga.org/api/v2/get/cameras" },
  { id: "gdoti-arcgis-unplanned", label: "GDOT ArcGIS Unplanned Traffic Interruptions", kind: "NEAR_REAL_TIME", access: "PUBLIC", enabled: true, authoritative: true, url: "https://enterprisegis.dot.ga.gov/server/rest/services/EOC/EOC_TRAFFIC_LAYERS/MapServer/1/query" },
  { id: "gdoti-arcgis-cameras", label: "GDOT ArcGIS CCTV Cameras", kind: "NEAR_REAL_TIME", access: "PUBLIC", enabled: true, authoritative: true, url: "https://enterprisegis.dot.ga.gov/hosting/rest/services/web_trafficcameras/MapServer/0/query" },
  { id: "waze-partner", label: "Waze for Cities Partner Feed", kind: "LIVE", access: "PARTNER", enabled: Boolean(process.env.WAZE_PARTNER_FEED_URL), authoritative: false, url: process.env.WAZE_PARTNER_FEED_URL, note: "Requires authorized partner feed URL; not a general public endpoint." },
  { id: "nhtsa-fars", label: "NHTSA FARS", kind: "HISTORICAL", access: "PUBLIC", enabled: false, authoritative: true, note: "Historical fatal-crash enrichment; not live incident ingestion." },
  { id: "fmcsa-ai", label: "FMCSA Analysis & Information", kind: "ENRICHMENT", access: "PUBLIC", enabled: false, authoritative: true, note: "Carrier safety/crash-history enrichment; not live incident ingestion." },
];

async function getJson(url: string, headers: Record<string, string> = {}): Promise<unknown> {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), TIMEOUT_MS);
  try {
    const response = await fetch(url, { headers: { Accept: "application/json", ...headers }, signal: controller.signal });
    if (!response.ok) throw new Error(`HTTP ${response.status} ${response.statusText}`);
    return await response.json();
  } finally {
    clearTimeout(timer);
  }
}

function unixToIso(value: unknown): string | undefined {
  const n = Number(value);
  return Number.isFinite(n) && n > 0 ? new Date(n * 1000).toISOString() : undefined;
}

function text(value: unknown): string | undefined {
  return typeof value === "string" && value.trim() ? value.trim() : undefined;
}

function number(value: unknown): number | undefined {
  const n = Number(value);
  return Number.isFinite(n) ? n : undefined;
}

function infer(description = ""): Pick<NormalizedTrafficEvent, "severityHint" | "commercialVehicleHint" | "injuryHint" | "fatalityHint" | "closureHint" | "stalledVehicleHint" | "debrisHint"> {
  const s = description.toLowerCase();
  const fatalityHint = /fatal|death|deceased/.test(s);
  const injuryHint = fatalityHint || /injur|ambulance|ems|hospital/.test(s);
  const commercialVehicleHint = /tractor[- ]?trailer|semi\b|18[- ]?wheeler|commercial vehicle|box truck|dump truck|bus\b|truck\b/.test(s);
  const closureHint = /all lanes.*closed|road closed|full closure|blocked/.test(s);
  const stalledVehicleHint = /stall|disabled vehicle|vehicle stopped/.test(s);
  const debrisHint = /debris|object in road|wheel[- ]?off|tire in road/.test(s);
  const severityHint = fatalityHint ? "critical" : injuryHint || closureHint || commercialVehicleHint ? "high" : stalledVehicleHint || debrisHint ? "medium" : "low";
  return { severityHint, commercialVehicleHint, injuryHint, fatalityHint, closureHint, stalledVehicleHint, debrisHint };
}

export async function fetchGdot511Events(): Promise<FetchResult<NormalizedTrafficEvent>> {
  const source = SOURCE_CATALOG.find((s) => s.id === "gdoti511-events")!;
  if (!source.enabled) return { source, fetchedAt: new Date().toISOString(), records: [], error: "GDOT_511_API_KEY is not configured" };
  try {
    const key = encodeURIComponent(process.env.GDOT_511_API_KEY!);
    const data = await getJson(`${source.url}?key=${key}&format=json`);
    const rows = Array.isArray(data) ? data : [];
    const records = rows.map((r: any): NormalizedTrafficEvent => {
      const description = text(r.Description) ?? text(r.EventType) ?? "Traffic event";
      const lat = number(r.Latitude), lon = number(r.Longitude);
      return {
        externalId: String(r.ID ?? r.Id ?? r.SourceId ?? crypto.randomUUID()),
        sourceId: source.id,
        sourceRecordType: "TrafficEvent",
        sourceUrl: source.url,
        observedAt: new Date().toISOString(),
        reportedAt: unixToIso(r.Reported),
        updatedAt: unixToIso(r.LastUpdated),
        roadway: text(r.RoadwayName ?? r.Roadway),
        direction: text(r.DirectionOfTravel ?? r.Direction),
        locationText: text(r.Location),
        point: lat !== undefined && lon !== undefined ? { latitude: lat, longitude: lon } : undefined,
        eventType: text(r.EventType ?? r.Type) ?? "UNKNOWN",
        description,
        lanesAffected: text(r.LanesAffected ?? r.Lanes),
        ...infer(description),
        raw: r,
      };
    });
    return { source, fetchedAt: new Date().toISOString(), records };
  } catch (error) {
    return { source, fetchedAt: new Date().toISOString(), records: [], error: error instanceof Error ? error.message : "Unknown source error" };
  }
}

export async function fetchArcGisUnplanned(): Promise<FetchResult<NormalizedTrafficEvent>> {
  const source = SOURCE_CATALOG.find((s) => s.id === "gdoti-arcgis-unplanned")!;
  try {
    const params = new URLSearchParams({ where: "1=1", outFields: "*", f: "geojson", outSR: "4326", returnGeometry: "true" });
    const data: any = await getJson(`${source.url}?${params.toString()}`);
    const features = Array.isArray(data?.features) ? data.features : [];
    const records = features.map((feature: any): NormalizedTrafficEvent => {
      const p = feature.properties ?? {};
      const coords = feature.geometry?.type === "Point" ? feature.geometry.coordinates : undefined;
      const description = text(p.DESCRIPTION ?? p.DESCRIPTIO ?? p.TYPE ?? p.EVENT_TYPE) ?? "Unplanned traffic interruption";
      return {
        externalId: String(p.OBJECTID ?? p.EVENT_ID ?? feature.id ?? crypto.randomUUID()),
        sourceId: source.id,
        sourceRecordType: "ArcGISFeature",
        sourceUrl: source.url,
        observedAt: new Date().toISOString(),
        roadway: text(p.ROUTE ?? p.ROADWAY ?? p.ROAD_NAME),
        direction: text(p.DIRECTION ?? p.DIR),
        locationText: text(p.LOCATION ?? p.COUNTY_NAME),
        point: Array.isArray(coords) && coords.length >= 2 ? { longitude: Number(coords[0]), latitude: Number(coords[1]) } : undefined,
        eventType: text(p.TYPE ?? p.EVENT_TYPE) ?? "UNPLANNED_TRAFFIC_INTERRUPTION",
        description,
        ...infer(description),
        raw: feature,
      };
    });
    return { source, fetchedAt: new Date().toISOString(), records };
  } catch (error) {
    return { source, fetchedAt: new Date().toISOString(), records: [], error: error instanceof Error ? error.message : "Unknown source error" };
  }
}

export async function fetchAuthorizedWazeFeed(): Promise<FetchResult<NormalizedTrafficEvent>> {
  const source = SOURCE_CATALOG.find((s) => s.id === "waze-partner")!;
  if (!source.enabled || !source.url) return { source, fetchedAt: new Date().toISOString(), records: [], error: "WAZE_PARTNER_FEED_URL is not configured" };
  try {
    const headers: Record<string, string> = {};
    if (process.env.WAZE_PARTNER_FEED_TOKEN) headers.Authorization = `Bearer ${process.env.WAZE_PARTNER_FEED_TOKEN}`;
    const data: any = await getJson(source.url, headers);
    const rows = Array.isArray(data) ? data : Array.isArray(data?.incidents) ? data.incidents : [];
    const records = rows.map((r: any): NormalizedTrafficEvent => {
      const description = text(r.description) ?? `${r.type ?? "INCIDENT"} ${r.subtype ?? ""}`.trim();
      const firstPoint = Array.isArray(r.polyline) ? r.polyline[0] : undefined;
      return {
        externalId: String(r.id ?? crypto.randomUUID()),
        sourceId: source.id,
        sourceRecordType: "WazePartnerIncident",
        sourceUrl: source.url,
        observedAt: new Date().toISOString(),
        reportedAt: text(r.starttime),
        updatedAt: text(r.updated_at),
        roadway: text(r.street),
        direction: text(r.direction),
        locationText: text(r.location),
        point: firstPoint && Number.isFinite(Number(firstPoint.lat)) && Number.isFinite(Number(firstPoint.lon)) ? { latitude: Number(firstPoint.lat), longitude: Number(firstPoint.lon) } : undefined,
        eventType: text(r.subtype ?? r.type) ?? "WAZE_INCIDENT",
        description,
        ...infer(description),
        raw: r,
      };
    });
    return { source, fetchedAt: new Date().toISOString(), records };
  } catch (error) {
    return { source, fetchedAt: new Date().toISOString(), records: [], error: error instanceof Error ? error.message : "Unknown source error" };
  }
}

export async function fetchLiveGeorgiaTraffic(): Promise<FetchResult<NormalizedTrafficEvent>[]> {
  return Promise.all([fetchGdot511Events(), fetchArcGisUnplanned(), fetchAuthorizedWazeFeed()]);
}
