import { Router, Request, Response } from "express";
import { scoreIntake, ScoreIntakeInput } from "../ai/scoring";

export const scoringRouter = Router();

function isFiniteUnit(value: unknown): boolean {
  return typeof value === "number" && Number.isFinite(value) && value >= 0 && value <= 1;
}

function validateScoreInput(input: any): string[] {
  const errors: string[] = [];
  const scores = input?.scores ?? {};
  for (const key of ["liability", "injury", "collectability", "evidence", "defendantResolution"]) {
    if (!isFiniteUnit(scores[key])) errors.push(`scores.${key} must be a number in [0,1]`);
  }
  if (!input?.mechanism || typeof input.mechanism !== "string") errors.push("mechanism is required");
  if (!Number.isInteger(input?.evidenceCount) || input.evidenceCount < 0) errors.push("evidenceCount must be a non-negative integer");
  if (!Number.isInteger(input?.numParties) || input.numParties < 0) errors.push("numParties must be a non-negative integer");
  if (!Number.isInteger(input?.numResolvedParties) || input.numResolvedParties < 0) errors.push("numResolvedParties must be a non-negative integer");
  if (input?.numResolvedParties > input?.numParties) errors.push("numResolvedParties cannot exceed numParties");
  if (!Number.isInteger(input?.contradictions?.highSeverityUnresolved) || input.contradictions.highSeverityUnresolved < 0) {
    errors.push("contradictions.highSeverityUnresolved must be a non-negative integer");
  }
  if (!Number.isInteger(input?.contradictions?.other) || input.contradictions.other < 0) {
    errors.push("contradictions.other must be a non-negative integer");
  }
  return errors;
}

/** Internal canonical scoring endpoint. It performs no contact-eligibility decision. */
scoringRouter.post("/score", (req: Request, res: Response) => {
  const errors = validateScoreInput(req.body);
  if (errors.length) return res.status(400).json({ error: "invalid_score_input", details: errors });

  const result = scoreIntake(req.body as ScoreIntakeInput);
  return res.json({
    result,
    policy: {
      contactEligibilityEvaluated: false,
      legalAccessBasisEvaluated: false,
      solicitationReviewEvaluated: false,
    },
  });
});
