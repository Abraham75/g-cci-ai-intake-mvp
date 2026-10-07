import { FetchResult, NormalizedTrafficEvent, SourceDescriptor } from "./types";

export const GDOT_511_ALERTS_SOURCE: SourceDescriptor = {
  id: "gdoti511-alerts",
  label: "GDOT 511 Alerts",
  kind: "LIVE",
  access: "API_KEY",
  enabled: Boolean(process.env.GDOT_511_API_KEY),
  authoritative: true,
  url: "https://511ga.org/api/v2/get/alerts",
};

function unixToIso(value: unknown): string | undefined {
  const n = Number(value);
  return Number.isFinite(n) && n > 0 ? new Date(n * 1000).toISOString() : undefined;
}

export async function fetchGdot511Alerts(): Promise<FetchResult<NormalizedTrafficEvent>> {
  if (!GDOT_511_ALERTS_SOURCE.enabled) {
    return { source: GDOT_511_ALERTS_SOURCE, fetchedAt: new Date().toISOString(), records: [], error: "GDOT_511_API_KEY is not configured" };
  }
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), Number(process.env.GCCI_SOURCE_TIMEOUT_MS ?? 8000));
  try {
    const params = new URLSearchParams({ key: process.env.GDOT_511_API_KEY!, format: "json" });
    const response = await fetch(`${GDOT_511_ALERTS_SOURCE.url}?${params.toString()}`, { signal: controller.signal, headers: { Accept: "application/json" } });
    if (!response.ok) throw new Error(`HTTP ${response.status} ${response.statusText}`);
    const body: any = await response.json();
    const rows = Array.isArray(body) ? body : [];
    const records = rows.map((r: any): NormalizedTrafficEvent => {
      const description = [r.Message, r.Notes].filter(Boolean).join(" — ") || "GDOT traffic alert";
      const lower = description.toLowerCase();
      return {
        externalId: String(r.Id ?? r.ID ?? `${r.StartTime ?? "alert"}-${description.slice(0, 40)}`),
        sourceId: GDOT_511_ALERTS_SOURCE.id,
        sourceRecordType: "TrafficAlert",
        sourceUrl: GDOT_511_ALERTS_SOURCE.url,
        observedAt: new Date().toISOString(),
        reportedAt: unixToIso(r.StartTime),
        updatedAt: unixToIso(r.LastUpdated),
        eventType: r.HighImportance ? "HIGH_IMPORTANCE_ALERT" : "TRAFFIC_ALERT",
        severityHint: r.HighImportance ? "high" : "medium",
        description,
        closureHint: /closed|closure|blocked/.test(lower),
        debrisHint: /debris|object in road|wheel[- ]?off|tire in road/.test(lower),
        stalledVehicleHint: /stall|disabled vehicle|vehicle stopped/.test(lower),
        commercialVehicleHint: /tractor[- ]?trailer|semi\b|18[- ]?wheeler|commercial vehicle|box truck|dump truck|bus\b|truck\b/.test(lower),
        injuryHint: /injur|ambulance|ems|hospital/.test(lower),
        fatalityHint: /fatal|death|deceased/.test(lower),
        raw: r,
      };
    });
    return { source: GDOT_511_ALERTS_SOURCE, fetchedAt: new Date().toISOString(), records };
  } catch (error) {
    return { source: GDOT_511_ALERTS_SOURCE, fetchedAt: new Date().toISOString(), records: [], error: error instanceof Error ? error.message : "Unknown source error" };
  } finally {
    clearTimeout(timer);
  }
}
