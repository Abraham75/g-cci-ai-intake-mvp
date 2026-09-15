import React, { useEffect, useState } from "react";
import { BarChart3, BriefcaseBusiness, LogIn, LogOut, Radio, Server, Scale, ShieldCheck } from "lucide-react";
import CaseIntelligenceDetail from "./CaseIntelligenceDetail.jsx";
import LeadQualificationWorkspace from "./LeadQualificationWorkspace.jsx";
import ContactComplianceVault from "./ContactComplianceVault.jsx";
import DecisionEconomicsDashboard from "./DecisionEconomicsDashboard.jsx";
import PlatformStatus from "./PlatformStatus.jsx";
import LiveSignals from "./LiveSignals.jsx";
import { initializeAuth, oidcConfigured, signIn, signOut, subscribeAuth } from "./auth.js";

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
  const [auth, setAuth] = useState({ loading: oidcConfigured, user: null, error: "" });

  useEffect(() => {
    let active = true;
    initializeAuth()
      .then((user) => {
        if (active) setAuth({ loading: false, user, error: "" });
      })
      .catch((error) => {
        if (active) {
          setAuth({
            loading: false,
            user: null,
            error: error instanceof Error ? error.message : "Authentication failed",
          });
        }
      });
    const unsubscribe = subscribeAuth((user) => {
      if (active) setAuth({ loading: false, user, error: "" });
    });
    return () => {
      active = false;
      unsubscribe();
    };
  }, []);

  const openCase = (hypothesisId) => {
    if (hypothesisId) setSelectedHypothesisId(hypothesisId);
    setView("case");
  };

  if (oidcConfigured && auth.loading) {
    return <AuthShell title="Authenticating…" text="Establishing the attorney-console session." />;
  }

  if (oidcConfigured && !auth.user) {
    return (
      <AuthShell
        title="G-CCI Sign In"
        text={auth.error || "Authentication is required before case intelligence can be accessed."}
        action={
          <button onClick={() => signIn()} className="flex items-center gap-2 px-4 py-2 bg-amber-500 text-slate-950 font-semibold rounded-lg hover:bg-amber-400">
            <LogIn size={16} /> Sign in with organization account
          </button>
        }
      />
    );
  }

  const displayName = auth.user?.profile?.name || auth.user?.profile?.preferred_username || "Authenticated user";

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
          Correlation, causation, attribution, case value, lead qualification, identity resolution, contact storage, and outreach eligibility remain separate decisions.
        </div>
      </aside>

      <div className="flex-1 min-w-0">
        <header className="h-14 bg-[#0a1628]/70 border-b border-slate-800 flex items-center justify-between px-6 sticky top-0 z-20 backdrop-blur">
          <div className="text-sm font-semibold text-slate-300">{NAV.find((item) => item.id === view)?.label}</div>
          <div className="flex items-center gap-4">
            <div className="text-[11px] text-slate-500">TypeScript canonical scorer · PostgreSQL/PostGIS intelligence · React attorney console</div>
            {oidcConfigured && (
              <button onClick={() => signOut()} className="flex items-center gap-1.5 text-[11px] text-slate-400 hover:text-slate-200" title={displayName}>
                <LogOut size={13} /> Sign out
              </button>
            )}
          </div>
        </header>
        <main className="p-6 max-w-[1600px] mx-auto">
          {view === "signals" && <LiveSignals onOpenCase={openCase} />}
          {view === "case" && (
            <>
              <CaseIntelligenceDetail hypothesisId={selectedHypothesisId} onBack={() => setView("signals")} />
              {selectedHypothesisId && <LeadQualificationWorkspace hypothesisId={selectedHypothesisId} />}
              {selectedHypothesisId && <ContactComplianceVault hypothesisId={selectedHypothesisId} />}
            </>
          )}
          {view === "economics" && <DecisionEconomicsDashboard />}
          {view === "status" && <PlatformStatus />}
        </main>
      </div>
    </div>
  );
}

function AuthShell({ title, text, action }) {
  return (
    <div className="min-h-screen bg-slate-950 text-slate-200 flex items-center justify-center p-6">
      <div className="w-full max-w-md bg-[#0f1f38] border border-slate-800 rounded-2xl p-7 text-center">
        <div className="flex items-center justify-center gap-2 text-amber-400 mb-4"><Scale size={24} /><span className="font-bold text-xl">G-CCI</span></div>
        <h1 className="text-xl font-bold">{title}</h1>
        <p className="text-sm text-slate-500 mt-2 mb-6">{text}</p>
        <div className="flex justify-center">{action}</div>
      </div>
    </div>
  );
}
