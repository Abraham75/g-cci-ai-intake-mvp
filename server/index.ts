import express from "express";
import cors from "cors";
import bodyParser from "body-parser";
import intakeRoute from "./routes/intake";
import ontologyRoute from "./routes/ontology";
import { complianceRouter } from "./compliance/gate";

const app = express();
app.use(cors());
app.use(bodyParser.json({ limit: "5mb" }));

app.use("/api", intakeRoute);
app.use("/api", ontologyRoute);
app.use("/api/compliance", complianceRouter);

const PORT = process.env.PORT || 3001;
app.listen(PORT, () => console.log(`Server running on port ${PORT}`));
