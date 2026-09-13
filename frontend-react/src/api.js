const API_BASE = import.meta.env.VITE_GCCI_API_BASE || "http://127.0.0.1:3001";
const CORRELATION_API_BASE =
  import.meta.env.VITE_GCCI_CORRELATION_API_BASE || "http://127.0.0.1:8000";
const DEV_AUTH_TOKEN = import.meta.env.DEV ? (import.meta.env.VITE_GCCI_AUTH_TOKEN || "") : "";

function runtimeAuthToken() {
  try {
    return window.sessionStorage.getItem("gcci_access_token") || DEV_AUTH_TOKEN;
  } catch {
    return DEV_AUTH_TOKEN;
  }
}

async function request(base, path, options = {}) {
  const authToken = runtimeAuthToken();
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

export function setRuntimeAccessToken(token) {
  window.sessionStorage.setItem("gcci_access_token", token);
}

export function clearRuntimeAccessToken() {
  window.sessionStorage.removeItem("gcci_access_token");
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
  readiness: () => request(CORRELATION_API_BASE, "/health/ready"),
  metrics: () => request(CORRELATION_API_BASE, "/metrics"),

  // Persistent PostGIS camera intelligence.
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

  // Lead Qualification & Resolution Engine.
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

  // Durable compliance and encrypted contact vault.
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
