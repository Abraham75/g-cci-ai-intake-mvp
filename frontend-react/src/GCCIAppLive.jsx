import React, { useEffect, useMemo, useState } from "react";
import { AlertTriangle, Briefcase, LayoutDashboard, RefreshCw, Search, ShieldCheck } from "lucide-react";
import { gcciApi } from "./api";

const TIER_LABEL = {
  A: "Tier A — Priority Investigation",
  B: "Tier B — High Potential",
  C: "Tier C — Evidence Development",
  D: "Tier D — Monitor",
};

function Badge({ children, tone = "slate" }) {
  const cls = {
    amber: "bg-amber-500/15 text-amber-300 border-amber-500/30",
    green: "bg-emerald-500/15 text-emerald-300 border-emerald-500/30",
    red: "bg-rose-500/15 text-rose-300 border-rose-500/30",
    sky: "bg-sky-500/15 text-sky-300 border-sky-500/30",
    slate: "bg-slate-800 text-slate-300 border-slate-700",
  }[tone];
  return <span className={`inline-flex px-2 py-1 rounded border text-[11px] font-semibold ${cls}`}>{children}</span>;
}

function Score({ label, value }) {
  const pct = Math.round((value || 0) * 100);
  return (
    <div>
      <div className="flex justify-between text-xs mb-1"><span className="text-slate-500">{label}</span><span>{pct}</span></div>
      <div className="h-2 rounded bg-slate-800 overflow-hidden"><div className="h-full bg-amber-500" style={{ width: `${pct}%` }} /></div>
    </div>
  );
}

export default function GCCIAppLive() {
  const [incidents, setIncidents] = useState([]);
  const [selectedId, setSelectedId] = useState("PhillipsIncident");
  const [search, setSearch] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [explain, setExplain] = useState(null);
  const [ledger, setLedger] = useState(null);

  const load = async () => {
    setLoading(true);
    setError("");
    try {
      const [rows, ledgerStatus] = await Promise.all([gcciApi.listIncidents(), gcciApi.verifyLedger()]);
      setIncidents(rows);
      setLedger(ledgerStatus);
      if (!rows.some((r) => r.id === selectedId) && rows[0]) setSelectedId(rows[0].id);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, []);

  const selected = incidents.find((i) => i.id === selectedId) || incidents[0];
  const filtered = useMemo(() => {
    const q = search.trim().toLowerCase();
    if (!q) return incidents;
    return incidents.filter((i) => [i.id, i.label, i.location, i.type, ...(i.vehicleTypes || [])].join(" ").toLowerCase().includes(q));
  }, [incidents, search]);

  const kpis = useMemo(() => ({
    total: incidents.length,
    high: incidents.filter((i) => i.tier === "A").length,
    cmv: incidents.filter((i) => i.isCMV).length,
    avg: incidents.length ? Math.round(incidents.reduce((s, i) => s + i.cos, 0) / incidents.length * 100) : 0,
  }), [incidents]);

  const runHypothesisAction = async (hypothesisId, action) => {
    await gcciApi.hypothesisAction(hypothesisId, action, `Action recorded from React MVP: ${action}`);
    await load();
  };

  const reviewParty = async (party) => {
    await gcciApi.complianceReview(party.id, {
      legalAccessBasis: "PublicRecord",
      solicitationReview: "ClearedByCounsel",
      suppressionChecked: true,
    });
    await load();
  };

  const openExplain = async () => {
    if (!selected) return;
    setExplain(await gcciApi.explainIncident(selected.id));
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-200">
      <header className="border-b border-slate-800 bg-[#0a1628] px-6 py-4 flex items-center justify-between sticky top-0 z-20">
        <div><div className="text-amber-400 font-bold text-xl">G-CCI</div><div className="text-xs text-slate-500">Live FastAPI-backed litigation intelligence MVP</div></div>
        <div className="flex items-center gap-3">
          {ledger && <Badge tone={ledger.valid ? "green" : "red"}><ShieldCheck size={12} className="mr-1" />Ledger {ledger.valid ? "Verified" : "Invalid"} · {ledger.entries}</Badge>}
          <button onClick={load} className="p-2 rounded bg-slate-800 hover:bg-slate-700"><RefreshCw size={16} /></button>
        </div>
      </header>

      <main className="p-6 space-y-6 max-w-[1600px] mx-auto">
        {error && <div className="border border-rose-700 bg-rose-950/40 text-rose-300 p-4 rounded-xl">Backend connection failed: {error}</div>}

        <section className="grid grid-cols-4 gap-4">
          {[
            ["Incidents", kpis.total, LayoutDashboard],
            ["Tier A", kpis.high, Briefcase],
            ["CMV", kpis.cmv, AlertTriangle],
            ["Avg COS", kpis.avg, ShieldCheck],
          ].map(([label, value, Icon]) => <div key={label} className="bg-[#0f1f38] border border-slate-800 rounded-xl p-4"><Icon size={16} className="text-amber-400 mb-2"/><div className="text-xs text-slate-500 uppercase">{label}</div><div className="text-2xl font-bold">{value}</div></div>)}
        </section>

        <section className="grid grid-cols-[380px_1fr] gap-6">
          <div className="bg-[#0f1f38] border border-slate-800 rounded-xl overflow-hidden">
            <div className="p-4 border-b border-slate-800">
              <div className="relative"><Search size={15} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500"/><input value={search} onChange={(e)=>setSearch(e.target.value)} placeholder="Search incidents..." className="w-full bg-slate-900 border border-slate-700 rounded pl-9 pr-3 py-2 text-sm"/></div>
            </div>
            <div className="max-h-[720px] overflow-y-auto">
              {loading && <div className="p-4 text-slate-500">Loading from FastAPI…</div>}
              {filtered.map((i) => <button key={i.id} onClick={()=>setSelectedId(i.id)} className={`w-full text-left p-4 border-b border-slate-800 hover:bg-slate-900 ${selected?.id===i.id ? "bg-amber-500/10" : ""}`}>
                <div className="flex justify-between gap-3"><div className="font-semibold text-sm">{i.label}</div><div className="text-amber-400 font-bold">{Math.round(i.cos*100)}</div></div>
                <div className="text-xs text-slate-500 mt-1">{i.location} · {i.type}</div>
                <div className="mt-2 flex gap-2"><Badge tone={i.tier==="A"?"amber":i.tier==="C"?"sky":"slate"}>{TIER_LABEL[i.tier]}</Badge>{i.isCMV && <Badge tone="green">CMV</Badge>}</div>
              </button>)}
            </div>
          </div>

          {selected && <div className="space-y-5">
            <div className="bg-[#0f1f38] border border-slate-800 rounded-xl p-5">
              <div className="flex justify-between items-start">
                <div><div className="text-xs text-amber-400 uppercase font-bold">Case Opportunity</div><h1 className="text-2xl font-bold mt-1">{selected.label}</h1><div className="text-sm text-slate-500 mt-1">{selected.id} · {selected.location}</div></div>
                <div className="text-right"><div className="text-4xl font-bold text-amber-400">{Math.round(selected.cos*100)}</div><Badge tone={selected.tier==="A"?"amber":selected.tier==="C"?"sky":"slate"}>{TIER_LABEL[selected.tier]}</Badge></div>
              </div>
              <button onClick={openExplain} className="mt-4 px-4 py-2 bg-amber-500 text-slate-950 font-semibold rounded">Explain This Decision</button>
            </div>

            <div className="grid grid-cols-2 gap-5">
              <div className="bg-[#0f1f38] border border-slate-800 rounded-xl p-5 space-y-3">
                <h2 className="font-semibold">Case Opportunity Components</h2>
                <Score label="Liability" value={selected.scores.liability}/><Score label="Injury" value={selected.scores.injury}/><Score label="Collectability" value={selected.scores.collectability}/><Score label="Evidence" value={selected.scores.evidence}/><Score label="Mechanism Severity" value={selected.scores.mechanismSeverity}/><Score label="Defendant Resolution" value={selected.scores.defendantResolution}/>
                <div className="text-xs text-rose-400">Uncertainty penalty: {Math.round(selected.scores.uncertaintyPenalty*100)}</div>
              </div>
              <div className="bg-[#0f1f38] border border-slate-800 rounded-xl p-5 space-y-4">
                <h2 className="font-semibold">Independent Confidence Measures</h2>
                <div><div className="text-xs text-sky-400 uppercase">Event Correlation</div><div className="text-3xl font-bold">{Math.round(selected.confidence.eventCorrelation*100)}</div></div>
                <div><div className="text-xs text-emerald-400 uppercase">Causal Relationship</div><div className="text-3xl font-bold">{Math.round(selected.confidence.causalRelationship*100)}</div></div>
                <div><div className="text-xs text-rose-400 uppercase">Party Attribution</div><div className="text-3xl font-bold">{Math.round(selected.confidence.partyAttribution*100)}</div></div>
              </div>
            </div>

            <div className="bg-[#0f1f38] border border-slate-800 rounded-xl p-5">
              <h2 className="font-semibold mb-3">Hypotheses — Ledger-backed Human Review</h2>
              <div className="space-y-3">{selected.hypotheses.length===0 && <div className="text-slate-500 text-sm">No hypotheses.</div>}{selected.hypotheses.map((h)=><div key={h.id} className="bg-slate-900/60 rounded p-4"><div className="flex justify-between"><div className="text-sm">{h.description}</div><div className="font-bold">{Math.round(h.confidence*100)}</div></div><div className="text-xs text-slate-500 mt-2">Machine confidence is immutable · Status: {h.status} {h.analystDecision ? `· ${h.analystDecision}` : ""}</div><div className="flex gap-2 mt-3"><button onClick={()=>runHypothesisAction(h.id,"confirm")} className="px-3 py-1 bg-emerald-700 rounded text-xs">Confirm</button><button onClick={()=>runHypothesisAction(h.id,"reject")} className="px-3 py-1 bg-rose-800 rounded text-xs">Reject</button><button onClick={()=>runHypothesisAction(h.id,"request-evidence")} className="px-3 py-1 bg-slate-700 rounded text-xs">Request Evidence</button></div></div>)}</div>
            </div>

            <div className="bg-[#0f1f38] border border-slate-800 rounded-xl p-5">
              <h2 className="font-semibold mb-3">Party Resolution & Compliance Gate</h2>
              <div className="space-y-3">{selected.parties.length===0 && <div className="text-slate-500 text-sm">No parties.</div>}{selected.parties.map((p)=>{const eligible=p.legalAccessBasis!=="NotEstablished"&&p.solicitationReview==="ClearedByCounsel"&&p.suppressionChecked;return <div key={p.id} className="bg-slate-900/60 rounded p-4 flex items-center justify-between"><div><div className="font-semibold text-sm">{p.role} · {p.stage}</div><div className="text-xs text-slate-500">{p.note}</div><div className="text-xs mt-1">Access: {p.legalAccessBasis} · Review: {p.solicitationReview} · Suppression: {String(p.suppressionChecked)}</div></div><div className="text-right"><Badge tone={eligible?"green":"slate"}>{eligible?"CONTACT ELIGIBLE":"NOT CONTACT ELIGIBLE"}</Badge><button onClick={()=>reviewParty(p)} className="block ml-auto mt-2 text-xs px-3 py-1 bg-sky-700 rounded">Run Demo Compliance Review</button></div></div>})}</div>
            </div>
          </div>}
        </section>
      </main>

      {explain && <div className="fixed inset-0 bg-black/70 flex items-center justify-center p-6 z-50" onClick={()=>setExplain(null)}><div className="max-w-2xl w-full bg-[#0f1f38] border border-slate-700 rounded-xl p-6 max-h-[80vh] overflow-y-auto" onClick={(e)=>e.stopPropagation()}><div className="flex justify-between"><h2 className="font-bold text-xl">Explain This Decision</h2><button onClick={()=>setExplain(null)}>✕</button></div><p className="mt-4 text-slate-300">{explain.scoreNarrative}</p><h3 className="mt-5 text-sm font-semibold text-amber-400">Supporting Evidence</h3>{explain.supportingEvidence.map((x)=><div key={x} className="text-sm text-slate-400">• {x}</div>)}<h3 className="mt-5 text-sm font-semibold text-rose-400">Contradictions</h3>{explain.contradictoryEvidence.length?explain.contradictoryEvidence.map((x)=><div key={x} className="text-sm text-slate-400">• {x}</div>):<div className="text-sm text-slate-500">None</div>}<h3 className="mt-5 text-sm font-semibold text-sky-400">Recommended Actions</h3>{explain.recommendedActions.map((x)=><div key={x} className="text-sm text-slate-400">• {x}</div>)}<div className="mt-5 text-xs text-slate-500">{explain.modelVersion} · {explain.sourceProvenance}</div></div></div>}
    </div>
  );
}
