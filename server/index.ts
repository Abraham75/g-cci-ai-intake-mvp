import express from "express";
import cors from "cors";
import bodyParser from "body-parser";
import intakeRoute from "./routes/intake";
import ontologyRoute from "./routes/ontology";
import { complianceRouter } from "./compliance/gate";
import { contradictionsRouter } from "./ai/contradictions";
import { signalsRouter } from "./routes/signals";
import { scoringRouter } from "./routes/scoring";

const app = express();
app.use(cors());
app.use(bodyParser.json({ limit: "5mb" }));

app.use("/api", intakeRoute);
app.use("/api", ontologyRoute);
app.use("/api/compliance", complianceRouter);
app.use("/api/contradictions", contradictionsRouter);
app.use("/api/signals", signalsRouter);
app.use("/api/scoring", scoringRouter);

const PORT = process.env.PORT || 3001;
app.listen(PORT, () => console.log(`Server running on port ${PORT}`));
