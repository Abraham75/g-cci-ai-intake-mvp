import { scoreIntake } from "./scoring";

export function triageIntake(payload: any) {
  const scoring = scoreIntake(payload);

  return {
    intakeId: crypto.randomUUID(),
    receivedAt: new Date().toISOString(),
    scoring,
    payload
  };
}
