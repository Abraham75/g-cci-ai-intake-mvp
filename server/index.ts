import express, { NextFunction, Request, Response } from "express";
import cors from "cors";
import bodyParser from "body-parser";
import { randomUUID } from "crypto";
import intakeRoute from "./routes/intake";
import ontologyRoute from "./routes/ontology";
import { contradictionsRouter } from "./ai/contradictions";
import { signalsRouter } from "./routes/signals";
import { scoringRouter } from "./routes/scoring";
import { apiAuth } from "./security/auth";

const app = express();
app.disable("x-powered-by");

const configuredOrigins = (process.env.GCCI_CORS_ORIGINS || "")
  .split(",")
  .map((value) => value.trim())
  .filter(Boolean);
const developmentOrigins = ["http://127.0.0.1:5173", "http://localhost:5173"];
const allowedOrigins = process.env.NODE_ENV === "production" ? configuredOrigins : [...configuredOrigins, ...developmentOrigins];

app.use(cors({
  origin(origin, callback) {
    // Non-browser service-to-service calls do not carry Origin and remain allowed.
    if (!origin) return callback(null, true);
    return callback(null, allowedOrigins.includes(origin));
  },
  methods: ["GET", "POST", "OPTIONS"],
  allowedHeaders: ["Authorization", "Content-Type", "X-Request-ID"],
  exposedHeaders: ["X-Request-ID"],
  credentials: true,
}));
app.use(bodyParser.json({ limit: "5mb" }));
app.use(apiAuth);
app.use((req: Request, res: Response, next: NextFunction) => {
  const requestId = req.header("x-request-id") || randomUUID();
  const started = process.hrtime.bigint();
  res.setHeader("X-Request-ID", requestId);
  res.locals.requestId = requestId;
  res.on("finish", () => {
    const durationMs = Number(process.hrtime.bigint() - started) / 1_000_000;
    console.log(JSON.stringify({
      level: "info",
      event: "http_request",
      requestId,
      method: req.method,
      path: req.path,
      status: res.statusCode,
      durationMs: Math.round(durationMs * 100) / 100,
      actorRole: res.locals.actor?.role || null,
      actorName: res.locals.actor?.name || null,
    }));
  });
  next();
});

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
    requestId: res.locals.requestId || null,
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
