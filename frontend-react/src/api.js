const API_BASE = import.meta.env.VITE_GCCI_API_BASE || "http://127.0.0.1:3001";

async function request(path) {
  const response = await fetch(`${API_BASE}${path}`);
  if (!response.ok) {
    const text = await response.text();
    throw new Error(`${response.status} ${response.statusText}: ${text}`);
  }
  return response.json();
}

export const gcciApi = {
  ontology: () => request("/api/ontology"),
  ledgerIntegrity: () => request("/api/ledger/integrity"),
};
