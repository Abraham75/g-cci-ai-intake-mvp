import React, { useEffect, useState } from "react";
import { AlertTriangle, Database, RefreshCw, Server, ShieldCheck } from "lucide-react";
import { gcciApi } from "./api.js";

export default function PlatformStatus() {
  const [status, setStatus] = useState({ loading: true, error: "", ontology: null, ledger: null, readiness: null, dependencies: null, metrics: null });

  const load = async () => {
    setStatus((current) => ({ ...current, loading: true, error: "" }));
    try {
      const [ontology, ledger, readiness, dependencies, metrics] = await Promise.all([
        gcciApi.ontology(),
        gcciApi.persistentLedgerIntegrity(),
        gcciApi.readiness(),
        gcciApi.dependencyHealth(),
        gcciApi.metrics().catch(() => null),
      ]);
      setStatus({ loading: false, error: "", ontology, ledger, readiness, dependencies, metrics });
    } catch (error) {
      setStatus({
        loading: false,
        error: error instanceof Error ? error.message : "Unknown runtime error",
        ontology: null,
        ledger: null,
        readiness: null,
        dependencies: null,
        metrics: null,
      });
    }
  };

  useEffect(() => { load(); }, []);

  return (
    <div className="space-y-6">
      <div className="flex items-start justify-between gap-4">
        <div>
          <div className="text-[11px] uppercase tracking-widest text-sky-400 font-bold mb-1">Production Operations</div>
          <h1 className="text-2xl font-bold text-slate-100">Platform Status</h1>
          <p className="text-[13px] text-slate-500 mt-1">Durable database, ledger, canonical scorer, camera inventory, and work-queue health.</p>
        </div>
        <button onClick={load} className="flex items-center gap-2 px-3 py-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-sm"><RefreshCw size={15} /> Refresh</button>
      </div>

      {status.error && <div className="rounded-xl border border-rose-800 bg-rose-950/30 p-4 flex gap-3"><AlertTriangle className="text-rose-400 shrink-0" size={18} /><div><div className="font-semibold text-rose-300">Production API unavailable</div><div className="text-sm text-rose-200/70 mt-1">{status.error}</div></div></div>}

      <div className="grid md:grid-cols-2 xl:grid-cols-4 gap-5">
        <StatusCard icon={Database} title="API / Database" value={status.readiness?.status?.toUpperCase() || "—"} ok={status.readiness?.status === "ready"} detail="Required PostgreSQL/PostGIS schema and database connectivity." />
        <StatusCard icon={ShieldCheck} title="Decision Ledger" value={status.ledger ? (status.ledger.valid ? "VALID" : "INVALID") : "—"} ok={Boolean(status.ledger?.valid)} detail={status.ledger?.error || "Persistent SHA-256 hash chain verification."} />
        <StatusCard icon={Server} title="Canonical Scorer" value={status.dependencies?.canonicalScorer?.ok ? "HEALTHY" : status.dependencies ? "DEGRADED" : "—"} ok={Boolean(status.dependencies?.canonicalScorer?.ok)} detail={status.dependencies?.canonicalScorer?.error || "Internal authenticated TypeScript scoring runtime."} />
        <StatusCard icon={Server} title="Camera Inventory" value={status.dependencies ? String(status.dependencies.cameraInventory?.active ?? 0) : "—"} ok={Boolean(status.dependencies && (status.dependencies.cameraInventory?.active ?? 0) > 0)} detail={`Active cameras · last seen ${formatDate(status.dependencies?.cameraInventory?.lastSeenAt)}`} />
      </div>

      <div className="grid lg:grid-cols-2 gap-5">
        <div className="bg-[#0f1f38] border border-slate-800 rounded-xl p-5">
          <div className="flex items-center gap-2 mb-3"><Server size={17} className="text-sky-400" /><h2 className="font-semibold">Ontology Contract</h2></div>
          {status.loading ? <div className="text-slate-500">Loading…</div> : status.ontology ? <><div className="text-2xl font-bold text-slate-100">{status.ontology.version}</div><div className="mt-4 space-y-2">{status.ontology.invariants?.map((item) => <div key={item} className="text-xs bg-slate-900/60 rounded px-3 py-2 text-slate-400">{item}</div>)}</div></> : <div className="text-slate-500">No ontology response.</div>}
        </div>

        <div className="bg-[#0f1f38] border border-slate-800 rounded-xl p-5">
          <div className="text-sm font-semibold mb-4">Operational Queue Counters</div>
          {!status.metrics ? <div className="text-slate-500 text-sm">Metrics unavailable for this role.</div> : (
            <div className="grid grid-cols-2 gap-3 text-xs">
              {Object.entries(status.metrics).map(([key, value]) => <div key={key} className="bg-slate-900/60 rounded-lg p-3"><div className="text-2xl font-bold text-slate-100">{value}</div><div className="text-[10px] text-slate-500 mt-1 break-words">{key}</div></div>)}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function StatusCard({ icon: Icon, title, value, ok, detail }) {
  return <div className="bg-[#0f1f38] border border-slate-800 rounded-xl p-5"><div className="flex items-center gap-2 mb-3"><Icon size={17} className={ok ? "text-emerald-400" : "text-amber-400"}/><h2 className="font-semibold text-sm">{title}</h2></div><div className={`text-2xl font-bold ${ok ? "text-emerald-400" : "text-amber-300"}`}>{value}</div><p className="text-[11px] text-slate-500 mt-2 leading-relaxed">{detail}</p></div>;
}

function formatDate(value) {
  if (!value) return "never";
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? String(value) : date.toLocaleString();
}
