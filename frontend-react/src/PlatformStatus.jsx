import React, { useEffect, useState } from "react";
import { RefreshCw, ShieldCheck, Server, AlertTriangle } from "lucide-react";
import { gcciApi } from "./api";

export default function PlatformStatus() {
  const [status, setStatus] = useState({ loading: true, error: "", ontology: null, ledger: null });

  const load = async () => {
    setStatus((current) => ({ ...current, loading: true, error: "" }));
    try {
      const [ontology, ledger] = await Promise.all([gcciApi.ontology(), gcciApi.ledgerIntegrity()]);
      setStatus({ loading: false, error: "", ontology, ledger });
    } catch (error) {
      setStatus({ loading: false, error: error instanceof Error ? error.message : "Unknown runtime error", ontology: null, ledger: null });
    }
  };

  useEffect(() => { load(); }, []);

  return (
    <div className="space-y-6">
      <div className="flex items-start justify-between gap-4">
        <div>
          <div className="text-[11px] uppercase tracking-widest text-sky-400 font-bold mb-1">Canonical TypeScript Runtime</div>
          <h1 className="text-2xl font-bold text-slate-100">Platform Status</h1>
          <p className="text-[13px] text-slate-500 mt-1">Live status for the ontology contract and provenance ledger exposed by server/.</p>
        </div>
        <button onClick={load} className="flex items-center gap-2 px-3 py-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-sm"><RefreshCw size={15} /> Refresh</button>
      </div>

      {status.error && <div className="rounded-xl border border-rose-800 bg-rose-950/30 p-4 flex gap-3"><AlertTriangle className="text-rose-400 shrink-0" size={18} /><div><div className="font-semibold text-rose-300">Backend connection unavailable</div><div className="text-sm text-rose-200/70 mt-1">{status.error}</div><div className="text-xs text-slate-500 mt-2">Start the canonical runtime with <code>npm run server</code> at the repository root.</div></div></div>}

      <div className="grid md:grid-cols-2 gap-5">
        <div className="bg-[#0f1f38] border border-slate-800 rounded-xl p-5">
          <div className="flex items-center gap-2 mb-3"><Server size={17} className="text-sky-400" /><h2 className="font-semibold">Ontology Contract</h2></div>
          {status.loading ? <div className="text-slate-500">Loading…</div> : status.ontology ? <><div className="text-2xl font-bold text-slate-100">{status.ontology.version}</div><div className="mt-4 space-y-2">{status.ontology.invariants?.map((item) => <div key={item} className="text-xs bg-slate-900/60 rounded px-3 py-2 text-slate-400">{item}</div>)}</div></> : <div className="text-slate-500">No ontology response.</div>}
        </div>

        <div className="bg-[#0f1f38] border border-slate-800 rounded-xl p-5">
          <div className="flex items-center gap-2 mb-3"><ShieldCheck size={17} className="text-emerald-400" /><h2 className="font-semibold">Decision Ledger Integrity</h2></div>
          {status.loading ? <div className="text-slate-500">Loading…</div> : status.ledger ? <><div className={`text-3xl font-bold ${status.ledger.valid ? "text-emerald-400" : "text-rose-400"}`}>{status.ledger.valid ? "VALID" : "INVALID"}</div><p className="text-sm text-slate-500 mt-2">Checks the current in-memory sequential hash chain. Durable persistence remains future production work.</p></> : <div className="text-slate-500">No ledger response.</div>}
        </div>
      </div>
    </div>
  );
}
