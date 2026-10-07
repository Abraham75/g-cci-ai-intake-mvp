import { Router, Request, Response } from "express";
import { SOURCE_CATALOG, fetchLiveGeorgiaTraffic } from "../integrations/georgiaTraffic";
import { fetchPublicGdotCameras } from "../integrations/georgiaCameras";
import { fetchGemaWazeAlerts, GEMA_WAZE_SOURCE } from "../integrations/gema";
import { fetchGdot511Alerts, GDOT_511_ALERTS_SOURCE } from "../integrations/gdot511Alerts";
import { ledgerOpportunitySignals, synthesizeOpportunitySignals } from "../ai/opportunitySignals";

export const signalsRouter = Router();

async function fetchAllLiveSources() {
  const [trafficResults, gema, alerts] = await Promise.all([
    fetchLiveGeorgiaTraffic(),
    fetchGemaWazeAlerts(),
    fetchGdot511Alerts(),
  ]);
  return [...trafficResults, gema, alerts];
}

signalsRouter.get("/sources", (_req: Request, res: Response) => {
  const byId = new Map([...SOURCE_CATALOG, GEMA_WAZE_SOURCE, GDOT_511_ALERTS_SOURCE].map((source) => [source.id, source]));
  const allSources = [...byId.values()];
  res.json({
    generatedAt: new Date().toISOString(),
    sources: allSources.map(({ url, ...source }) => ({ ...source, endpointConfigured: Boolean(url) })),
    policy: {
      subject: "incident opportunity signals",
      personIdentification: false,
      outreachAuthorization: false,
      complianceGateRequiredBeforeContact: true,
    },
  });
});

signalsRouter.get("/live", async (_req: Request, res: Response) => {
  const results = await fetchAllLiveSources();
  const events = results.flatMap((result) => result.records);
  const signals = synthesizeOpportunitySignals(events);
  res.json({
    fetchedAt: new Date().toISOString(),
    sourceStatus: results.map((result) => ({ sourceId: result.source.id, records: result.records.length, error: result.error ?? null })),
    signals,
  });
});

signalsRouter.post("/live/ledger", async (_req: Request, res: Response) => {
  const results = await fetchAllLiveSources();
  const signals = synthesizeOpportunitySignals(results.flatMap((result) => result.records));
  ledgerOpportunitySignals(signals);
  res.status(201).json({ ledgered: signals.length, signals });
});

signalsRouter.get("/cameras", async (_req: Request, res: Response) => {
  try {
    const cameras = await fetchPublicGdotCameras();
    res.json({ fetchedAt: new Date().toISOString(), count: cameras.length, cameras });
  } catch (error) {
    res.status(502).json({ error: error instanceof Error ? error.message : "Camera source failure" });
  }
});
