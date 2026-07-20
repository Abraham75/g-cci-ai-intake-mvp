const API_BASE = import.meta.env.VITE_GCCI_API_BASE || "http://127.0.0.1:8000";

async function request(path, options = {}) {
  const response = await fetch(`${API_BASE}${path}`, {
    headers: { "Content-Type": "application/json", ...(options.headers || {}) },
    ...options,
  });
  if (!response.ok) {
    const text = await response.text();
    throw new Error(`${response.status} ${response.statusText}: ${text}`);
  }
  return response.json();
}

export const gcciApi = {
  listIncidents: () => request("/api/incidents"),
  getIncident: (id) => request(`/api/incidents/${encodeURIComponent(id)}`),
  explainIncident: (id) => request(`/api/incidents/${encodeURIComponent(id)}/explain`),
  hypothesisAction: (id, action, analystNote = "") => request(
    `/api/hypotheses/${encodeURIComponent(id)}/${action}`,
    { method: "POST", body: JSON.stringify({ analystNote }) },
  ),
  complianceReview: (partyId, body) => request(
    `/api/parties/${encodeURIComponent(partyId)}/compliance-review`,
    { method: "POST", body: JSON.stringify(body) },
  ),
  verifyLedger: () => request("/api/ledger/verify"),
};
