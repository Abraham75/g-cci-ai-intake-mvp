import React, { useEffect, useMemo, useState } from "react";
import { AlertTriangle, Camera, RefreshCw, ShieldCheck, Truck, MapPin, ArrowRight } from "lucide-react";

const API_BASE = import.meta.env.VITE_GCCI_API_BASE || "http://127.0.0.1:3001";

export default function LiveSignals({ onOpenCase }) {
  const [data, setData] = useState({ signals: [], sourceStatus: [] });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const load = async () => {
    setLoading(true); setError("");
    try {
      const response = await fetch(`${API_BASE}/api/signals/live`);
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      setData(await response.json());
    } catch (e) {
      setError(e instanceof Error ? e.message : "Unknown source error");
    } finally { setLoading(false); }
  };

  useEffect(() => { load(); }, []);

  const counts = useMemo(() => ({
    total: data.signals.length,
    cmv: data.signals.filter((s) => s.event.commercialVehicleHint).length,
    high: data.signals.filter((s) => s.tier === "A" || s.tier === "B").length,
  }), [data]);

  return (
    <div className="space-y-6">
      <div className="flex items-start justify-between gap-4">
        <div><div className="text-[11px] uppercase tracking-widest text-amber-400 font-bold">Public Incident Intelligence</div><h1 className="text-2xl font-bold text-slate-100">Live Georgia Opportunity Signals</h1><p className="text-[12px] text-slate-500 mt-1">Ranks incidents for attorney investigation. It does not identify people or authorize outreach.</p></div>
        <button onClick={load} disabled={loading} className="flex items-center gap-2 px-3 py-2 bg-slate-800 rounded-lg text-sm hover:bg-slate-700 disabled:opacity-50"><RefreshCw size={14} className={loading ? "animate-spin" : ""}/>Refresh</button>
      </div>

      <div className="grid md:grid-cols-3 gap-4">
        <Card icon={AlertTriangle} label="Live normalized incidents" value={counts.total}/>
        <Card icon={Truck} label="Commercial-vehicle signals" value={counts.cmv}/>
        <Card icon={ShieldCheck} label="Tier A/B investigations" value={counts.high}/>
      </div>

      <div className="bg-[#0f1f38] border border-slate-800 rounded-xl p-4">
        <div className="text-xs font-semibold mb-3">Source Health</div>
        <div className="grid md:grid-cols-3 gap-2">{data.sourceStatus.map((s) => <div key={s.sourceId} className="bg-slate-900/60 rounded p-3 text-[11px]"><div className="font-semibold text-slate-300">{s.sourceId}</div><div className="text-slate-500">{s.records} records</div>{s.error && <div className="text-amber-400 mt-1">{s.error}</div>}</div>)}</div>
      </div>

      {error && <div className="border border-rose-800 bg-rose-950/30 text-rose-300 rounded-xl p-4 text-sm">{error}</div>}

      <div className="space-y-3">
        {data.signals.map((s) => {
          // The live public-signal endpoint may or may not already have a persisted
          // IncidentHypothesis. We only expose the drill-down action when it provides
          // an authoritative hypothesis identifier; the UI never invents one.
          const hypothesisId = s.hypothesisId || s.incidentHypothesisId || s.hypothesis?.id;
          return <div key={s.id} className="bg-[#0f1f38] border border-slate-800 rounded-xl p-4">
            <div className="flex items-start justify-between gap-4"><div><div className="flex items-center gap-2"><span className="font-semibold text-slate-100">{s.event.eventType}</span>{s.event.commercialVehicleHint && <span className="text-[10px] px-2 py-0.5 rounded bg-amber-900/50 text-amber-300">CMV SIGNAL</span>}</div><div className="text-[12px] text-slate-500 mt-1 flex flex-wrap gap-3">{s.event.roadway && <span>{s.event.roadway}</span>}{s.event.direction && <span>{s.event.direction}</span>}{s.event.point && <span className="flex items-center gap-1"><MapPin size={11}/>{s.event.point.latitude.toFixed(4)}, {s.event.point.longitude.toFixed(4)}</span>}</div></div><div className="text-right"><div className="text-2xl font-bold text-amber-400">{Math.round(s.score * 100)}</div><div className="text-[10px] text-slate-500">Tier {s.tier}</div></div></div>
            {s.event.description && <div className="text-[13px] text-slate-300 mt-3">{s.event.description}</div>}
            <div className="mt-3 flex flex-wrap gap-1">{s.reasons.map((r) => <span key={r} className="text-[10px] px-2 py-1 bg-slate-900 rounded text-slate-400">{r}</span>)}</div>
            <div className="mt-3 pt-3 border-t border-slate-800 grid md:grid-cols-2 gap-4"><div><div className="text-[10px] uppercase text-sky-400 font-bold mb-1">Recommended evidence development</div>{s.recommendedEvidence.map((r) => <div key={r} className="text-[11px] text-slate-500">• {r}</div>)}</div><div className="text-[11px] text-slate-500"><div className="flex items-center gap-1 text-emerald-400"><Camera size={12}/> Source: {s.event.sourceId}</div><div className="mt-2 text-amber-400">Outreach permitted: NO — compliance gate required.</div>{hypothesisId ? <button onClick={() => onOpenCase?.(hypothesisId)} className="mt-3 flex items-center gap-2 px-3 py-2 bg-amber-500 text-slate-950 font-semibold rounded-lg hover:bg-amber-400">Open Case Intelligence <ArrowRight size={13}/></button> : <div className="mt-3 text-[10px] text-slate-600">Case detail becomes available after this signal is persisted into an IncidentHypothesis.</div>}</div></div>
          </div>;
        })}
      </div>
    </div>
  );
}

function Card({ icon: Icon, label, value }) { return <div className="bg-[#0f1f38] border border-slate-800 rounded-xl p-4"><Icon size={16} className="text-amber-400 mb-2"/><div className="text-2xl font-bold">{value}</div><div className="text-[11px] text-slate-500">{label}</div></div>; }
