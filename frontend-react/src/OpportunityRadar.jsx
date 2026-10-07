import React, { useEffect, useMemo, useState } from "react";
import { ArrowRight, CheckCircle2, Clock3, RefreshCw, Target, XCircle } from "lucide-react";
import { gcciApi } from "./api.js";

const REVIEWER = import.meta.env.VITE_GCCI_REVIEWER || "attorney-console";

export default function OpportunityRadar({ onOpenCase }) {
  const [items, setItems] = useState([]);
  const [metrics, setMetrics] = useState(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const load = async () => {
    setLoading(true); setError("");
    try {
      const [opportunities, validation] = await Promise.all([
        gcciApi.opportunities(50),
        gcciApi.validationMetrics(10),
      ]);
      setItems(opportunities);
      setMetrics(validation);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Unable to load opportunity radar");
    } finally { setLoading(false); }
  };

  useEffect(() => { load(); }, []);

  const counts = useMemo(() => ({
    total: items.length,
    urgent: items.filter((item) => item.tier === "A").length,
    high: items.filter((item) => item.tier === "A" || item.tier === "B").length,
    unreviewed: items.filter((item) => !item.attorneyReview).length,
  }), [items]);

  const review = async (hypothesisId, disposition, attorneyWorthy) => {
    try {
      await gcciApi.recordAttorneyReview(hypothesisId, {
        disposition,
        attorney_worthy: attorneyWorthy,
        reviewed_by: REVIEWER,
      });
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Review could not be recorded");
    }
  };

  return <div className="space-y-6">
    <div className="flex items-start justify-between gap-4">
      <div>
        <div className="text-[11px] uppercase tracking-widest text-amber-400 font-bold">Attorney Priority Queue</div>
        <h1 className="text-2xl font-bold text-slate-100">Opportunity Radar</h1>
        <p className="text-[12px] text-slate-500 mt-1">Ranked cases first. Human dispositions become the ground truth used to validate G-CCI.</p>
      </div>
      <button onClick={load} disabled={loading} className="flex items-center gap-2 px-3 py-2 bg-slate-800 rounded-lg text-sm hover:bg-slate-700 disabled:opacity-50">
        <RefreshCw size={14} className={loading ? "animate-spin" : ""}/>Refresh
      </button>
    </div>

    <div className="grid md:grid-cols-4 gap-3">
      <Stat label="Ranked opportunities" value={counts.total}/>
      <Stat label="Tier A — investigate now" value={counts.urgent}/>
      <Stat label="Tier A/B" value={counts.high}/>
      <Stat label="Awaiting attorney review" value={counts.unreviewed}/>
    </div>

    <div className="bg-[#0f1f38] border border-slate-800 rounded-xl p-4">
      <div className="flex items-center gap-2 text-sm font-semibold"><Target size={15} className="text-amber-400"/>Validation — not vanity metrics</div>
      <div className="grid md:grid-cols-5 gap-4 mt-3 text-sm">
        <Metric label="Discovery recall" value={pct(metrics?.discoveryRecall)} />
        <Metric label="Precision@10" value={pct(metrics?.precisionAtK)} />
        <Metric label="Qualification precision" value={pct(metrics?.qualificationPrecision)} />
        <Metric label="Investigation yield" value={pct(metrics?.investigationYield)} />
        <Metric label="Reviewed ground truth" value={metrics?.counts?.reviewed ?? "—"} />
      </div>
      <div className="text-[10px] text-slate-600 mt-3">Discovery recall appears only after known valuable cases are loaded into the external benchmark corpus and matched with evidence.</div>
    </div>

    {error && <div className="border border-rose-800 bg-rose-950/30 text-rose-300 rounded-xl p-4 text-sm">{error}</div>}

    <div className="space-y-3">
      {items.map((item, index) => <div key={item.hypothesisId} className="bg-[#0f1f38] border border-slate-800 rounded-xl p-5">
        <div className="flex items-start justify-between gap-5">
          <div className="flex gap-4">
            <div className="text-2xl font-black text-slate-600">#{index + 1}</div>
            <div>
              <div className="flex items-center gap-2">
                <span className="font-semibold text-slate-100">{item.roadway || "Roadway unresolved"} {item.direction || ""}</span>
                <span className={`text-[10px] px-2 py-0.5 rounded font-bold ${item.tier === "A" ? "bg-rose-950 text-rose-300" : "bg-amber-950 text-amber-300"}`}>TIER {item.tier}</span>
              </div>
              <div className="text-[11px] text-slate-500 mt-1">{new Date(item.startTime).toLocaleString()} · hypothesis {item.hypothesisId}</div>
            </div>
          </div>
          <div className="text-right"><div className="text-3xl font-bold text-amber-400">{Math.round(item.score * 100)}</div><div className="text-[9px] uppercase tracking-wider text-slate-600">Case opportunity</div></div>
        </div>

        <div className="mt-4 grid md:grid-cols-[1fr_auto] gap-4 border-t border-slate-800 pt-4">
          <div>
            <div className="text-[10px] uppercase tracking-wider text-sky-400 font-bold">Next best action</div>
            <div className="text-sm text-slate-300 mt-1">{item.nextBestAction?.recommendedAction || "Attorney review — no open evidence task."}</div>
            {item.nextBestAction && <div className="text-[10px] text-slate-600 mt-1">{item.nextBestAction.evidenceType} · priority {Math.round(item.nextBestAction.priority * 100)}</div>}
          </div>
          <button onClick={() => onOpenCase?.(item.hypothesisId)} className="self-center flex items-center gap-2 px-3 py-2 bg-amber-500 text-slate-950 font-semibold rounded-lg hover:bg-amber-400 text-sm">Open case <ArrowRight size={13}/></button>
        </div>

        <div className="mt-4 flex flex-wrap items-center gap-2">
          <span className="text-[10px] uppercase text-slate-600 mr-1">Attorney disposition</span>
          <button onClick={() => review(item.hypothesisId, "GOOD_CASE", true)} className="flex items-center gap-1 px-2.5 py-1.5 rounded bg-emerald-950/50 text-emerald-300 text-xs hover:bg-emerald-900"><CheckCircle2 size={12}/>Worth investigating</button>
          <button onClick={() => review(item.hypothesisId, "NEEDS_MORE_INFORMATION", null)} className="flex items-center gap-1 px-2.5 py-1.5 rounded bg-slate-800 text-slate-300 text-xs hover:bg-slate-700"><Clock3 size={12}/>Need more info</button>
          <button onClick={() => review(item.hypothesisId, "BAD_CASE", false)} className="flex items-center gap-1 px-2.5 py-1.5 rounded bg-rose-950/40 text-rose-300 text-xs hover:bg-rose-900"><XCircle size={12}/>Not worth pursuing</button>
          {item.attorneyReview && <span className="text-[10px] text-slate-500 ml-2">Latest: {item.attorneyReview.disposition.replaceAll("_", " ")}</span>}
        </div>
      </div>)}
      {!loading && items.length === 0 && <div className="text-sm text-slate-500 border border-dashed border-slate-800 rounded-xl p-8 text-center">No scored opportunities yet. The radar populates only after durable correlation and canonical scoring.</div>}
    </div>
  </div>;
}

function Stat({ label, value }) { return <div className="bg-[#0f1f38] border border-slate-800 rounded-xl p-4"><div className="text-2xl font-bold">{value}</div><div className="text-[11px] text-slate-500">{label}</div></div>; }
function Metric({ label, value }) { return <div><div className="text-xl font-bold text-slate-200">{value}</div><div className="text-[10px] text-slate-500">{label}</div></div>; }
function pct(value) { return value == null ? "Not enough data" : `${Math.round(value * 100)}%`; }
