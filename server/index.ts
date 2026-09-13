import express, { NextFunction, Request, Response } from "express";
import cors from "cors";
import bodyParser from "body-parser";
import intakeRoute from "./routes/intake";
import ontologyRoute from "./routes/ontology";
import { contradictionsRouter } from "./ai/contradictions";
import { signalsRouter } from "./routes/signals";
import { scoringRouter } from "./routes/scoring";

const app = express();
app.disable("x-powered-by");
app.use(cors());
app.use(bodyParser.json({ limit: "5mb" }));

app.get("/health/live", (_req: Request, res: Response) => {
  return res.json({ status: "ok", service: "gcci-canonical-typescript-runtime" });
});

app.use("/api", intakeRoute);
app.use("/api", ontologyRoute);
// Compliance/contact eligibility is intentionally NOT mounted here. PostgreSQL/PostGIS
// is now the single authoritative compliance store exposed by the Python service.
app.use("/api/contradictions", contradictionsRouter);
app.use("/api/signals", signalsRouter);
app.use("/api/scoring", scoringRouter);

app.use((err: unknown, req: Request, res: Response, _next: NextFunction) => {
  const message = err instanceof Error ? err.message : "Unknown server error";
  console.error(JSON.stringify({
    level: "error",
    service: "gcci-canonical-typescript-runtime",
    method: req.method,
    path: req.path,
    message,
  }));
  return res.status(500).json({ error: "internal_server_error" });
});

const PORT = process.env.PORT || 3001;
app.listen(PORT, () => console.log(JSON.stringify({
  level: "info",
  service: "gcci-canonical-typescript-runtime",
  port: Number(PORT),
})));
