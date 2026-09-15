import { getAccessToken } from "./auth.js";

const CORRELATION_API_BASE =
  import.meta.env.VITE_GCCI_CORRELATION_API_BASE || "http://127.0.0.1:8000";

async function request(base, path, options = {}) {
  const authToken = await getAccessToken();
  const authHeaders = authToken ? { Authorization: `Bearer ${authToken}` } : {};
  const response = await fetch(`${base}${path}`, {
    headers: {
      "Content-Type": "application/json",
      ...authHeaders,
      ...(options.headers || {}),
    },
    ...options,
  });
  if (!response.ok) {
    const text = await response.text();
    throw new Error(`${response.status} ${response.statusText}: ${text}`);
  }
  return response.json();
}

export const gcciApi = {
  // Single external API boundary. The Python service proxies safe internal runtime reads.
  ontology: () => request(CORRELATION_API_BASE, "/runtime/ontology"),
  liveSignals: () => request(CORRELATION_API_BASE, "/signals/live"),
  readiness: () => request(CORRELATION_API_BASE, "/health/ready"),
  dependencyHealth: () => request(CORRELATION_API_BASE, "/health/dependencies"),
  metrics: () => request(CORRELATION_API_BASE, "/metrics"),
  ledgerIntegrity: () => request(CORRELATION_API_BASE, "/ledger/integrity"),
  persistentLedgerIntegrity: () => request(CORRELATION_API_BASE, "/ledger/integrity"),

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

  cameraStatus: () => request(CORRELATION_API_BASE, "/cameras/status"),
  hypothesisCameras: (hypothesisId, currentOnly = true) =>
    request(
      CORRELATION_API_BASE,
      `/hypotheses/${encodeURIComponent(hypothesisId)}/cameras?current_only=${currentOnly ? "true" : "false"}`,
    ),
  refreshHypothesisCameras: (hypothesisId) =>
    request(
      CORRELATION_API_BASE,
      `/hypotheses/${encodeURIComponent(hypothesisId)}/cameras/refresh`,
      { method: "POST" },
    ),

  leadQualification: (hypothesisId) =>
    request(CORRELATION_API_BASE, `/hypotheses/${encodeURIComponent(hypothesisId)}/qualification`),
  refreshLeadQualification: (hypothesisId) =>
    request(
      CORRELATION_API_BASE,
      `/hypotheses/${encodeURIComponent(hypothesisId)}/qualification/refresh`,
      { method: "POST" },
    ),
  resolutionTasks: (hypothesisId, openOnly = true) =>
    request(
      CORRELATION_API_BASE,
      `/hypotheses/${encodeURIComponent(hypothesisId)}/resolution-tasks?open_only=${openOnly ? "true" : "false"}`,
    ),
  prospects: (hypothesisId) =>
    request(CORRELATION_API_BASE, `/hypotheses/${encodeURIComponent(hypothesisId)}/prospects`),
  recordProspectEvidence: (hypothesisId, evidence) =>
    request(
      CORRELATION_API_BASE,
      `/hypotheses/${encodeURIComponent(hypothesisId)}/prospects/evidence`,
      { method: "POST", body: JSON.stringify(evidence) },
    ),

  complianceGate: (hypothesisId) =>
    request(CORRELATION_API_BASE, `/hypotheses/${encodeURIComponent(hypothesisId)}/compliance`),
  reviewCompliance: (hypothesisId, review) =>
    request(
      CORRELATION_API_BASE,
      `/hypotheses/${encodeURIComponent(hypothesisId)}/compliance/review`,
      { method: "POST", body: JSON.stringify(review) },
    ),
  contacts: (hypothesisId) =>
    request(CORRELATION_API_BASE, `/hypotheses/${encodeURIComponent(hypothesisId)}/contacts`),
  addContact: (hypothesisId, contact) =>
    request(
      CORRELATION_API_BASE,
      `/hypotheses/${encodeURIComponent(hypothesisId)}/contacts`,
      { method: "POST", body: JSON.stringify(contact) },
    ),
  setContactStatus: (contactId, status, reason) =>
    request(
      CORRELATION_API_BASE,
      `/contacts/${encodeURIComponent(contactId)}/status`,
      { method: "POST", body: JSON.stringify({ status, reason }) },
    ),
  revealContact: (contactId, reason) =>
    request(
      CORRELATION_API_BASE,
      `/contacts/${encodeURIComponent(contactId)}/reveal`,
      { method: "POST", body: JSON.stringify({ reason }) },
    ),
  activateOutreach: (hypothesisId) =>
    request(
      CORRELATION_API_BASE,
      `/hypotheses/${encodeURIComponent(hypothesisId)}/activate`,
      { method: "POST" },
    ),
};
