import express from "express";
import { triageIntake } from "../ai/triage";

const router = express.Router();

router.post("/intake", async (req, res) => {
  try {
    const result = triageIntake(req.body);

    console.log("INTAKE RECEIVED:", result);

    res.status(200).json({
      status: "received",
      intakeId: result.intakeId,
      tier: result.scoring.tier
    });
  } catch (err) {
    res.status(500).json({ error: "Intake processing failed" });
  }
});

export default router;
