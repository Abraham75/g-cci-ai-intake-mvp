import { Router, Request, Response } from "express";
import { SOURCE_CATALOG, fetchLiveGeorgiaTraffic } from "../integrations/georgiaTraffic";
import { fetchPublicGdotCameras } from "../integrations/georgiaCameras";
import { ledgerOpportunitySignals, synthesizeOpportunitySignals } from "../ai/opportunitySignals";

export const signalsRouter = Router();

signalsRouter.get("/sources", (_req: Request, res: Response) => {
  res.json({
    generatedAt: new Date().toISOString(),
    sources: SOURCE_CATALOG.map(({ url, ...source }) => ({ ...source, endpointConfigured: Boolean(url) })),
    policy: {
      subject: "incident opportunity signals",
      personIdentification: false,
      outreachAuthorization: false,
      complianceGateRequiredBeforeContact: true,
    },
  });
});

signalsRouter.get("/live", async (_req: Request, res: Response) => {
  const results = await fetchLiveGeorgiaTraffic();
  const events = results.flatMap((result) => result.records);
  const signals = synthesizeOpportunitySignals(events);
  res.json({
    fetchedAt: new Date().toISOString(),
    sourceStatus: results.map((result) => ({ sourceId: result.source.id, records: result.records.length, error: result.error ?? null })),
    signals,
  });
});

signalsRouter.post("/live/ledger", async (_req: Request, res: Response) => {
  const results = await fetchLiveGeorgiaTraffic();
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
