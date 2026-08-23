const API_BASE = import.meta.env.VITE_GCCI_API_BASE || "http://127.0.0.1:3001";
const CORRELATION_API_BASE =
  import.meta.env.VITE_GCCI_CORRELATION_API_BASE || "http://127.0.0.1:8000";

async function request(base, path) {
  const response = await fetch(`${base}${path}`);
  if (!response.ok) {
    const text = await response.text();
    throw new Error(`${response.status} ${response.statusText}: ${text}`);
  }
  return response.json();
}

export const gcciApi = {
  // Canonical TypeScript runtime.
  ontology: () => request(API_BASE, "/api/ontology"),
  ledgerIntegrity: () => request(API_BASE, "/api/ledger/integrity"),

  // Durable PostgreSQL/PostGIS correlation runtime.
  hypothesis: (hypothesisId) =>
    request(CORRELATION_API_BASE, `/hypotheses/${encodeURIComponent(hypothesisId)}`),
  hypothesisRevisions: (hypothesisId) =>
    request(CORRELATION_API_BASE, `/hypotheses/${encodeURIComponent(hypothesisId)}/revisions`),
  currentScore: (hypothesisId) =>
    request(CORRELATION_API_BASE, `/hypotheses/${encodeURIComponent(hypothesisId)}/score`),
  scoreHistory: (hypothesisId) =>
    request(CORRELATION_API_BASE, `/hypotheses/${encodeURIComponent(hypothesisId)}/scores`),
  acquisitionTasks: (hypothesisId, openOnly = false) =>
    request(
      CORRELATION_API_BASE,
      `/hypotheses/${encodeURIComponent(hypothesisId)}/acquisition-tasks?open_only=${openOnly ? "true" : "false"}`,
    ),
  subjectLedger: (subjectId) =>
    request(CORRELATION_API_BASE, `/ledger/subject/${encodeURIComponent(subjectId)}`),
  persistentLedgerIntegrity: () => request(CORRELATION_API_BASE, "/ledger/integrity"),
};
