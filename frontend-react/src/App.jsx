import React, { useState } from "react";
import { BarChart3, BriefcaseBusiness, Radio, Server, Scale, ShieldCheck } from "lucide-react";
import CaseIntelligenceDetail from "./CaseIntelligenceDetail.jsx";
import DecisionEconomicsDashboard from "./DecisionEconomicsDashboard.jsx";
import PlatformStatus from "./PlatformStatus.jsx";
import LiveSignals from "./LiveSignals.jsx";

const DEFAULT_HYPOTHESIS_ID = import.meta.env.VITE_GCCI_DEMO_HYPOTHESIS_ID || "";

const NAV = [
  { id: "signals", label: "Live Opportunity Signals", icon: Radio },
  { id: "case", label: "Case Intelligence Detail", icon: BriefcaseBusiness },
  { id: "economics", label: "Decision Economics", icon: BarChart3 },
  { id: "status", label: "Platform Status", icon: Server },
];

export default function App() {
  const [view, setView] = useState("signals");
  const [selectedHypothesisId, setSelectedHypothesisId] = useState(DEFAULT_HYPOTHESIS_ID);

  const openCase = (hypothesisId) => {
    if (hypothesisId) setSelectedHypothesisId(hypothesisId);
    setView("case");
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-200 flex">
      <aside className="w-64 bg-[#0a1628] border-r border-slate-800 min-h-screen flex flex-col shrink-0">
        <div className="p-5 border-b border-slate-800">
          <div className="flex items-center gap-2 text-amber-400"><Scale size={20} /><span className="font-bold text-lg">G-CCI</span></div>
          <div className="text-[11px] text-slate-500 mt-1">Graham Case Correlation Intelligence</div>
        </div>
        <nav className="p-3 space-y-1">
          {NAV.map(({ id, label, icon: Icon }) => (
            <button key={id} onClick={() => setView(id)} className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-left text-sm transition ${view === id ? "bg-amber-500/10 text-amber-400" : "text-slate-400 hover:bg-slate-800/60 hover:text-slate-200"}`}>
              <Icon size={16} />{label}
            </button>
          ))}
        </nav>
        <div className="mt-auto p-4 border-t border-slate-800 text-[10px] text-slate-600 leading-relaxed">
          <div className="flex items-center gap-1.5 text-slate-500 mb-1"><ShieldCheck size={12} /> Compliance-first intelligence</div>
          Correlation, causation, attribution, case value, evidence priority, and contact eligibility remain separate decisions.
        </div>
      </aside>

      <div className="flex-1 min-w-0">
        <header className="h-14 bg-[#0a1628]/70 border-b border-slate-800 flex items-center justify-between px-6 sticky top-0 z-20 backdrop-blur">
          <div className="text-sm font-semibold text-slate-300">{NAV.find((item) => item.id === view)?.label}</div>
          <div className="text-[11px] text-slate-500">TypeScript canonical scorer · PostgreSQL/PostGIS correlation · React attorney console</div>
        </header>
        <main className="p-6 max-w-[1600px] mx-auto">
          {view === "signals" && <LiveSignals onOpenCase={openCase} />}
          {view === "case" && <CaseIntelligenceDetail hypothesisId={selectedHypothesisId} onBack={() => setView("signals")} />}
          {view === "economics" && <DecisionEconomicsDashboard />}
          {view === "status" && <PlatformStatus />}
        </main>
      </div>
    </div>
  );
}
