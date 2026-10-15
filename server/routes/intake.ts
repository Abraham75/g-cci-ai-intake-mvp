import express from "express";
import { triageIntake } from "../ai/triage";

const router = express.Router();

router.post("/intake", async (req, res) => {
  try {
    const result = triageIntake(req.body);

    console.log(JSON.stringify({
      level: "info",
      event: "intake_received",
      intakeId: result.intakeId,
      tier: result.scoring.tier,
    }));

    return res.status(200).json({
      status: "received",
      intakeId: result.intakeId,
      tier: result.scoring.tier,
    });
  } catch (err) {
    console.error(JSON.stringify({
      level: "error",
      event: "intake_processing_failed",
      message: err instanceof Error ? err.message : "unknown",
    }));
    return res.status(500).json({ error: "Intake processing failed" });
  }
});

export default router;
