import React, { useMemo, useState } from "react";
import { TrendingUp, AlertCircle, Clock, FileSearch, DollarSign, CheckCircle2, Info, Sliders, HelpCircle } from "lucide-react";
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell, LineChart, Line, Legend } from "recharts";

const ENGINE_OUTPUT = {
  totalIncidentsIngested: 1240,
  qualifiedOpportunities: 178,
  tierA: 24,
  tierB: 61,
  tierC: 93,
  evidenceGapsIdentified: 402,
  opportunitiesWithGaps: 151,
  contradictionsForcingReview: 19,
};

const MONTHLY_TREND = [
  { month: "Feb", qualified: 22, gaps: 51 },
  { month: "Mar", qualified: 28, gaps: 63 },
  { month: "Apr", qualified: 31, gaps: 70 },
  { month: "May", qualified: 34, gaps: 78 },
  { month: "Jun", qualified: 30, gaps: 69 },
  { month: "Jul", qualified: 33, gaps: 71 },
];

export default function DecisionEconomicsDashboard() {
  const [assumptions, setAssumptions] = useState({
    reviewMinutesPerOpportunity: 40,
    prescreenReductionPct: 60,
    avgCaseValueTierA: 180000,
    avgCaseValueTierB: 70000,
    signRateLiftPct: 12,
  });

  const set = (key, value) => setAssumptions((current) => ({ ...current, [key]: value }));

  const measured = {
    qualified: ENGINE_OUTPUT.qualifiedOpportunities,
    qualifyRate: Math.round((ENGINE_OUTPUT.qualifiedOpportunities / ENGINE_OUTPUT.totalIncidentsIngested) * 100),
    evidenceGaps: ENGINE_OUTPUT.evidenceGapsIdentified,
    gapCoverage: Math.round((ENGINE_OUTPUT.opportunitiesWithGaps / ENGINE_OUTPUT.qualifiedOpportunities) * 100),
  };

  const modeled = useMemo(() => {
    const reviewHoursAvoided = Math.round(
      (ENGINE_OUTPUT.totalIncidentsIngested - ENGINE_OUTPUT.qualifiedOpportunities) *
      (assumptions.reviewMinutesPerOpportunity / 60) *
      (assumptions.prescreenReductionPct / 100)
    );

    const blendedValue =
      (ENGINE_OUTPUT.tierA * assumptions.avgCaseValueTierA + ENGINE_OUTPUT.tierB * assumptions.avgCaseValueTierB) /
      Math.max(1, ENGINE_OUTPUT.tierA + ENGINE_OUTPUT.tierB);
    const modeledNewlySigned = Math.round((ENGINE_OUTPUT.tierA + ENGINE_OUTPUT.tierB) * (assumptions.signRateLiftPct / 100));
    const incrementalValue = Math.round(modeledNewlySigned * blendedValue);

    return { reviewHoursAvoided, incrementalValue, modeledNewlySigned, blendedValue: Math.round(blendedValue) };
  }, [assumptions]);

  const tierData = [
    { tier: "A", count: ENGINE_OUTPUT.tierA, color: "#f59e0b" },
    { tier: "B", count: ENGINE_OUTPUT.tierB, color: "#059669" },
    { tier: "C", count: ENGINE_OUTPUT.tierC, color: "#0284c7" },
  ];

  return (
    <div className="space-y-6">
      <div>
        <div className="text-[11px] uppercase tracking-widest text-amber-400 font-bold mb-1">Decision-Economics Platform</div>
        <h1 className="text-2xl font-bold text-slate-100">G-CCI — Case Acquisition Economics</h1>
        <p className="text-[13px] text-slate-500 mt-1">Reframing incident correlation into measurable decision value. Synthetic demonstration data.</p>
      </div>

      <div className="flex flex-wrap gap-4 text-[12px] bg-[#0f1f38] border border-slate-800 rounded-xl p-3">
        <span className="flex items-center gap-2"><CheckCircle2 size={14} className="text-emerald-400" /><b className="text-emerald-400">Measured</b> — derived from data the system actually holds</span>
        <span className="flex items-center gap-2"><Sliders size={14} className="text-amber-400" /><b className="text-amber-400">Modeled</b> — depends on adjustable assumptions; not an observed result</span>
        <span className="flex items-center gap-2"><HelpCircle size={14} className="text-slate-500" /><b className="text-slate-400">Not yet measurable</b> — requires real case outcomes</span>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-5 gap-4">
        <MetricCard kind="measured" icon={TrendingUp} label="Qualified Case Opportunities" value={measured.qualified} sub={`${measured.qualifyRate}% of ${ENGINE_OUTPUT.totalIncidentsIngested} ingested`} />
        <MetricCard kind="notmeasurable" icon={AlertCircle} label="False-Positive Rate" value="—" sub="Needs attorney disposition outcomes" />
        <MetricCard kind="modeled" icon={Clock} label="Attorney-Review Hours Avoided" value={modeled.reviewHoursAvoided.toLocaleString()} sub="Modeled from assumptions" />
        <MetricCard kind="measured" icon={FileSearch} label="Evidence Gaps Identified Pre-Intake" value={measured.evidenceGaps} sub={`${measured.gapCoverage}% of opportunities flagged`} />
        <MetricCard kind="modeled" icon={DollarSign} label="Incremental Expected Case Value" value={`$${(modeled.incrementalValue / 1e6).toFixed(2)}M`} sub="Modeled — see assumptions" />
      </div>

      <div className="bg-amber-950/20 border border-amber-800/40 rounded-xl p-4 flex gap-3">
        <HelpCircle size={18} className="text-amber-400 shrink-0 mt-0.5" />
        <div className="text-[12.5px] text-amber-100/80">
          <b className="text-amber-300">Why false-positive rate is blank:</b> it is an outcome metric. It becomes measurable only after attorneys disposition qualified opportunities and that feedback is written back into G-CCI. The decision ledger is the intended audit backbone for that future feedback loop.
        </div>
      </div>

      <div className="grid md:grid-cols-3 gap-6">
        <div className="md:col-span-2 bg-[#0f1f38] border border-slate-800 rounded-xl p-5">
          <div className="flex items-center gap-2 mb-4"><CheckCircle2 size={15} className="text-emerald-400" /><h2 className="text-sm font-semibold text-slate-200">Qualified Opportunities & Evidence Gaps Over Time</h2><span className="text-[10px] px-1.5 py-0.5 bg-emerald-900/50 text-emerald-300 rounded">MEASURED</span></div>
          <ResponsiveContainer width="100%" height={220}>
            <LineChart data={MONTHLY_TREND}>
              <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
              <XAxis dataKey="month" stroke="#64748b" fontSize={11} />
              <YAxis stroke="#64748b" fontSize={11} />
              <Tooltip contentStyle={{ background: "#0f1f38", border: "1px solid #334155", fontSize: 12 }} />
              <Legend wrapperStyle={{ fontSize: 12 }} />
              <Line type="monotone" dataKey="qualified" name="Qualified Opportunities" stroke="#f59e0b" strokeWidth={2} />
              <Line type="monotone" dataKey="gaps" name="Evidence Gaps Flagged" stroke="#0284c7" strokeWidth={2} />
            </LineChart>
          </ResponsiveContainer>
        </div>

        <div className="bg-[#0f1f38] border border-slate-800 rounded-xl p-5">
          <div className="flex items-center gap-2 mb-4"><CheckCircle2 size={15} className="text-emerald-400" /><h2 className="text-sm font-semibold text-slate-200">Opportunity Tier Mix</h2></div>
          <ResponsiveContainer width="100%" height={220}>
            <BarChart data={tierData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
              <XAxis dataKey="tier" stroke="#64748b" fontSize={11} />
              <YAxis stroke="#64748b" fontSize={11} allowDecimals={false} />
              <Tooltip contentStyle={{ background: "#0f1f38", border: "1px solid #334155", fontSize: 12 }} />
              <Bar dataKey="count" radius={[4, 4, 0, 0]}>{tierData.map((d) => <Cell key={d.tier} fill={d.color} />)}</Bar>
            </BarChart>
          </ResponsiveContainer>
          <div className="text-[11px] text-slate-500 mt-2">{ENGINE_OUTPUT.contradictionsForcingReview} opportunities currently require contradiction review in this synthetic dataset.</div>
        </div>
      </div>

      <div className="bg-[#0f1f38] border border-amber-800/40 rounded-xl p-5">
        <div className="flex items-center gap-2 mb-1"><Sliders size={16} className="text-amber-400" /><h2 className="text-sm font-semibold text-slate-200">Assumptions Behind the Modeled Metrics</h2><span className="text-[10px] px-1.5 py-0.5 bg-amber-900/50 text-amber-300 rounded">ADJUSTABLE</span></div>
        <p className="text-[12px] text-slate-500 mb-4">Change these inputs and the modeled metrics recompute immediately. They are assumptions, not observed firm outcomes.</p>
        <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-5">
          <Slider label="Manual review time per raw lead" unit="min" min={10} max={90} value={assumptions.reviewMinutesPerOpportunity} onChange={(v) => set("reviewMinutesPerOpportunity", v)} />
          <Slider label="Review effort removed by pre-screen" unit="%" min={10} max={90} value={assumptions.prescreenReductionPct} onChange={(v) => set("prescreenReductionPct", v)} />
          <Slider label="Modeled sign-rate lift" unit="%" min={2} max={30} value={assumptions.signRateLiftPct} onChange={(v) => set("signRateLiftPct", v)} />
          <Slider label="Avg. value — Tier A case" min={50000} max={400000} step={10000} value={assumptions.avgCaseValueTierA} onChange={(v) => set("avgCaseValueTierA", v)} money />
          <Slider label="Avg. value — Tier B case" min={20000} max={200000} step={5000} value={assumptions.avgCaseValueTierB} onChange={(v) => set("avgCaseValueTierB", v)} money />
        </div>
        <div className="mt-5 pt-4 border-t border-slate-800 grid md:grid-cols-3 gap-4 text-[12px]">
          <Derived label="Modeled newly-signed cases" value={modeled.modeledNewlySigned} />
          <Derived label="Blended avg case value" value={`$${modeled.blendedValue.toLocaleString()}`} />
          <Derived label="Incremental expected value" value={`$${(modeled.incrementalValue / 1e6).toFixed(2)}M`} highlight />
        </div>
      </div>

      <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-4 flex gap-3">
        <Info size={16} className="text-slate-500 shrink-0 mt-0.5" />
        <div className="text-[12px] text-slate-500"><b className="text-slate-400">Reading this dashboard:</b> measured values are counts from the synthetic demonstration dataset; modeled values depend on visible assumptions; false-positive rate remains unavailable until real attorney review outcomes exist.</div>
      </div>
    </div>
  );
}

function MetricCard({ kind, icon: Icon, label, value, sub }) {
  const styles = {
    measured: { ring: "border-emerald-800/50", tag: "MEASURED", tagCls: "bg-emerald-900/50 text-emerald-300", iconCls: "text-emerald-400" },
    modeled: { ring: "border-amber-800/50", tag: "MODELED", tagCls: "bg-amber-900/50 text-amber-300", iconCls: "text-amber-400" },
    notmeasurable: { ring: "border-slate-700", tag: "NOT YET", tagCls: "bg-slate-800 text-slate-400", iconCls: "text-slate-500" },
  };
  const style = styles[kind] ?? styles.notmeasurable;
  return <div className={`bg-[#0f1f38] border ${style.ring} rounded-xl p-4`}><div className="flex items-center justify-between mb-2"><Icon size={18} className={style.iconCls} /><span className={`text-[9px] px-1.5 py-0.5 rounded font-bold ${style.tagCls}`}>{style.tag}</span></div><div className="text-2xl font-bold text-slate-100">{value}</div><div className="text-[11px] text-slate-500 mt-1 leading-tight">{label}</div><div className="text-[10px] text-slate-600 mt-1">{sub}</div></div>;
}

function Slider({ label, unit = "", min, max, step = 1, value, onChange, money = false }) {
  return <div><div className="flex justify-between text-[11px] mb-1"><span className="text-slate-400">{label}</span><span className="text-amber-400 font-semibold">{money ? `$${value.toLocaleString()}` : `${value}${unit}`}</span></div><input type="range" min={min} max={max} step={step} value={value} onChange={(e) => onChange(Number(e.target.value))} className="w-full accent-amber-500" /></div>;
}

function Derived({ label, value, highlight = false }) {
  return <div className={`rounded-lg p-3 ${highlight ? "bg-amber-500/10 border border-amber-700/40" : "bg-slate-900/50"}`}><div className="text-[10px] uppercase text-slate-500 tracking-wide">{label}</div><div className={`text-lg font-bold ${highlight ? "text-amber-400" : "text-slate-200"}`}>{value}</div></div>;
}
