export function scoreIntake(intake: any) {
  let score = 0;
  const reasons: string[] = [];

  if (intake?.preQual?.incidentType === "truck") {
    score += 30;
    reasons.push("Commercial vehicle involved");
  }

  if (intake?.preQual?.severity >= 7) {
    score += 25;
    reasons.push("Severe injury");
  }

  if (intake?.incident?.description?.length > 200) {
    score += 15;
    reasons.push("Detailed incident narrative");
  }

  if (intake?.claimant?.email && intake?.claimant?.phone) {
    score += 10;
    reasons.push("Complete contact information");
  }

  const tier =
    score >= 60 ? "HIGH" :
    score >= 35 ? "MEDIUM" :
    "LOW";

  return {
    score,
    tier,
    reasons,
    reviewedAt: new Date().toISOString()
  };
}
