export interface CameraRecord {
  externalId: string;
  sourceId: "gdoti-arcgis-cameras";
  name?: string;
  roadway?: string;
  direction?: string;
  latitude?: number;
  longitude?: number;
  snapshotUrl?: string;
  streamUrl?: string;
  rawProperties: Record<string, unknown>;
}

const CAMERA_QUERY = "https://enterprisegis.dot.ga.gov/hosting/rest/services/web_trafficcameras/MapServer/0/query";

export async function fetchPublicGdotCameras(): Promise<CameraRecord[]> {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), Number(process.env.GCCI_SOURCE_TIMEOUT_MS ?? 8000));
  try {
    const params = new URLSearchParams({ where: "1=1", outFields: "*", f: "geojson", outSR: "4326", returnGeometry: "true" });
    const response = await fetch(`${CAMERA_QUERY}?${params.toString()}`, { signal: controller.signal, headers: { Accept: "application/geo+json, application/json" } });
    if (!response.ok) throw new Error(`GDOT camera query failed: HTTP ${response.status}`);
    const body: any = await response.json();
    const features = Array.isArray(body?.features) ? body.features : [];
    return features.map((f: any) => {
      const p = (f.properties ?? {}) as Record<string, unknown>;
      const c = f.geometry?.type === "Point" ? f.geometry.coordinates : undefined;
      const pick = (...keys: string[]): string | undefined => {
        for (const key of keys) {
          const v = p[key];
          if (typeof v === "string" && v.trim()) return v.trim();
        }
        return undefined;
      };
      return {
        externalId: String(p.OBJECTID ?? p.DEVICE_ID ?? p.DEVICE_NAME ?? f.id ?? "unknown-camera"),
        sourceId: "gdoti-arcgis-cameras" as const,
        name: pick("DEVICE_NAME", "CAMERA_NAME", "NAME"),
        roadway: pick("ROADWAY", "ROUTE", "ROAD_NAME"),
        direction: pick("DIRECTION", "DIR"),
        latitude: Array.isArray(c) ? Number(c[1]) : undefined,
        longitude: Array.isArray(c) ? Number(c[0]) : undefined,
        snapshotUrl: pick("SNAPSHOT_URL", "IMAGE_URL", "CAMERA_URL", "URL"),
        streamUrl: pick("STREAM_URL", "VIDEO_URL"),
        rawProperties: p,
      };
    });
  } finally {
    clearTimeout(timer);
  }
}
