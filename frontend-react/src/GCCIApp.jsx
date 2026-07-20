import React, { useState, useMemo } from "react";
import { LayoutDashboard, Briefcase, FileSearch, GitBranch, FileText, Lightbulb, AlertTriangle, Users, BarChart3, Settings, Search, X, ChevronRight, Info } from "lucide-react";
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell } from "recharts";

const mk = (o) => ({
  id: o.id, label: o.label, type: o.type, occurredAt: o.occurredAt, location: o.location,
  isCMV: o.isCMV ?? false, vehicleTypes: o.vehicleTypes ?? [],
  liabilitySignals: o.liabilitySignals ?? [], injurySignals: o.injurySignals ?? [],
  evidence: o.evidence ?? [], hypotheses: o.hypotheses ?? [], contradictions: o.contradictions ?? [],
  parties: o.parties ?? [],
  scores: { liability: 0.3, injury: 0.2, collectability: 0.2, evidence: 0.3, mechanismSeverity: 0.4, defendantResolution: 0.2, uncertaintyPenalty: 0, ...o.scores },
  confidence: { eventCorrelation: 0.6, causalRelationship: 0.4, partyAttribution: 0.2, ...o.confidence },
});

const INCIDENTS = [
  mk({
    id: "PhillipsIncident", label: "Phillips Incident", type: "Sideswipe Collision",
    occurredAt: "2025-12-09T14:20:00", location: "I-285 WB @ MM 24.5", isCMV: false,
    vehicleTypes: ["Passenger SUV"], liabilitySignals: ["MechanicalFailure"],
    injurySignals: ["ReportedInjury", "EMSResponse"],
    evidence: [
      { id: "ev_001", type: "Crash Report", source: "DEMO_GDOT", timestamp: "2025-12-09T14:25:00", factStatus: "Observed Fact", provenance: "Open Records Request (synthetic)" },
    ],
    hypotheses: [
      { id: "hyp_p1", description: "SUV struck by debris originating from a separate wheel-separation event (Event5122820) moments earlier, same roadway.", type: "SequentialCausationHypothesis", confidence: 0.74, supporting: ["ev_001"], contradicting: [], status: "MachineProposed", analystDecision: null },
      { id: "hyp_p2", description: "SUV struck by debris of unrelated, unidentified origin — no confirmed link to Event5122820.", type: "IndependentEventsHypothesis", confidence: 0.21, supporting: [], contradicting: ["ev_001"], status: "MachineProposed", analystDecision: null },
    ],
    parties: [
      { id: "party_001", role: "Injured Party", stage: "CANDIDATE", note: "Occupant of the SUV struck by debris.", legalAccessBasis: "NotEstablished", solicitationReview: "NotReviewed", suppressionChecked: false },
    ],
    scores: { liability: 0.4, injury: 0.5, collectability: 0.2, evidence: 0.35, mechanismSeverity: 0.6, defendantResolution: 0.15, uncertaintyPenalty: 0.1 },
    confidence: { eventCorrelation: 0.82, causalRelationship: 0.68, partyAttribution: 0.22 },
  }),
  mk({
    id: "Event5122820", label: "Event 5122820", type: "Wheel-Off Incident",
    occurredAt: "2025-12-09T13:53:00", location: "I-285 WB @ MM 24.8", isCMV: true,
    vehicleTypes: ["Unidentified Work Truck"], liabilitySignals: ["MechanicalFailure", "ImproperMaintenance"],
    injurySignals: [],
    evidence: [
      { id: "ev_002", type: "CCTV", source: "DEMO_GDOT_CCTV", timestamp: "2025-12-09T13:53:00", factStatus: "Observed Fact", provenance: "Restricted Government Data (synthetic)", attributes: { vehicle_color: "white", vehicle_type: "work_truck" } },
      { id: "ev_003", type: "Witness Statement", source: "DEMO_witness", timestamp: "2025-12-09T13:55:00", factStatus: "Allegation", provenance: "Discovery Obtainable (synthetic)", attributes: { vehicle_color: "blue" } },
    ],
    hypotheses: [
      { id: "hyp_e1", description: "Wheel separated from the commercial work truck due to a maintenance-related mechanical failure.", type: "VehicleFailureHypothesis", confidence: 0.58, supporting: ["ev_002"], contradicting: ["ev_003"], status: "MachineProposed", analystDecision: null },
      { id: "hyp_e2", description: "Event resulted from an unrelated cause; vehicle description conflict undermines the primary theory.", type: "IndependentEventsHypothesis", confidence: 0.34, supporting: ["ev_003"], contradicting: ["ev_002"], status: "MachineProposed", analystDecision: null },
    ],
    contradictions: [
      { id: "con_001", type: "vehicle_color_conflict", assertionA: "ev_002 (CCTV): vehicle_color = white", assertionB: "ev_003 (Witness): vehicle_color = blue", severity: "high", impactOnScore: -0.22, resolved: false },
    ],
    parties: [
      { id: "party_002", role: "Driver", stage: "UNKNOWN", note: "Operator of the unidentified work truck.", legalAccessBasis: "NotEstablished", solicitationReview: "NotReviewed", suppressionChecked: false },
      { id: "party_003", role: "Motor Carrier", stage: "CANDIDATE", note: "Carrier associated with the work truck (unverified).", legalAccessBasis: "NotEstablished", solicitationReview: "NotReviewed", suppressionChecked: false },
    ],
    scores: { liability: 0.6, injury: 0.0, collectability: 0.5, evidence: 0.4, mechanismSeverity: 0.9, defendantResolution: 0.15, uncertaintyPenalty: 0.22 },
    confidence: { eventCorrelation: 0.82, causalRelationship: 0.55, partyAttribution: 0.18 },
  }),
  mk({
    id: "INC-10204758", label: "Tractor-Trailer / Passenger Vehicle", type: "Angle Collision",
    occurredAt: "2025-11-02T08:12:00", location: "I-75 SB @ MM 112.3", isCMV: true,
    vehicleTypes: ["Tractor-Trailer", "Passenger Sedan"], liabilitySignals: ["ImproperLaneChange", "FollowingTooClosely"],
    injurySignals: ["ReportedInjury", "EMSResponse", "AirbagDeployment"],
    evidence: [
      { id: "ev_101", type: "Crash Report", source: "DEMO_GDOT", timestamp: "2025-11-02T08:20:00", factStatus: "Observed Fact", provenance: "Open Records Request (synthetic)" },
      { id: "ev_102", type: "CAD Record", source: "DEMO_CAD", timestamp: "2025-11-02T08:14:00", factStatus: "Observed Fact", provenance: "Public Record (synthetic)" },
      { id: "ev_103", type: "ELD", source: "DEMO_Carrier", timestamp: "2025-11-02T07:50:00", factStatus: "Observed Fact", provenance: "Discovery Obtainable (synthetic)" },
    ],
    hypotheses: [
      { id: "hyp_t1", description: "Tractor-trailer improper lane change caused the collision; ELD indicates no HOS violation.", type: "SequentialCausationHypothesis", confidence: 0.81, supporting: ["ev_101", "ev_103"], contradicting: [], status: "MachineProposed", analystDecision: null },
    ],
    parties: [
      { id: "party_101", role: "Motor Carrier", stage: "VERIFIED", note: "Carrier identity confirmed via synthetic FMCSA-style lookup.", legalAccessBasis: "PublicRecord", solicitationReview: "ClearedByCounsel", suppressionChecked: true },
      { id: "party_102", role: "Injured Party", stage: "CORROBORATED", note: "Driver of the sedan; role and involvement corroborated by crash report.", legalAccessBasis: "NotEstablished", solicitationReview: "WithinHoldPeriod", suppressionChecked: false },
    ],
    scores: { liability: 0.85, injury: 0.75, collectability: 0.9, evidence: 0.8, mechanismSeverity: 0.65, defendantResolution: 0.8, uncertaintyPenalty: 0 },
    confidence: { eventCorrelation: 0.95, causalRelationship: 0.88, partyAttribution: 0.7 },
  }),
  mk({ id: "INC-10167438", label: "Bobtail Lane-Change", type: "Angle Collision", occurredAt: "2025-10-14T16:40:00", location: "I-20 WB @ MM 5.0", isCMV: true, vehicleTypes: ["Bobtail Tractor"], liabilitySignals: ["ImproperLaneChange"], injurySignals: [], scores: { liability: 0.5, injury: 0.1, collectability: 0.5, evidence: 0.4, mechanismSeverity: 0.5, defendantResolution: 0.3, uncertaintyPenalty: 0 }, confidence: { eventCorrelation: 0.7, causalRelationship: 0.5, partyAttribution: 0.3 } }),
  mk({ id: "INC-10166139", label: "Passenger Intersection Collision", type: "Angle Collision", occurredAt: "2025-09-20T16:00:00", location: "I-675 SB @ MM 5.0", isCMV: false, vehicleTypes: ["Passenger Sedan", "Passenger Sedan"], liabilitySignals: [], injurySignals: [], scores: { liability: 0.1, injury: 0.0, collectability: 0.0, evidence: 0.0, mechanismSeverity: 0.4, defendantResolution: 0.0, uncertaintyPenalty: 0 }, confidence: { eventCorrelation: 0.4, causalRelationship: 0.2, partyAttribution: 0.05 } }),
  mk({ id: "INC-10167485", label: "Multi-Vehicle Sideswipe", type: "Sideswipe Collision", occurredAt: "2025-10-28T17:15:00", location: "I-85 NB @ MM 44.0", isCMV: false, vehicleTypes: ["Passenger SUV", "Passenger Hatchback"], liabilitySignals: ["DistractedDriving"], injurySignals: ["ReportedInjury"], scores: { liability: 0.45, injury: 0.3, collectability: 0.1, evidence: 0.25, mechanismSeverity: 0.5, defendantResolution: 0.2, uncertaintyPenalty: 0 }, confidence: { eventCorrelation: 0.6, causalRelationship: 0.45, partyAttribution: 0.25 } }),
  mk({ id: "INC-20391004", label: "Work-Zone Debris Strike", type: "Debris Incident", occurredAt: "2025-08-11T11:05:00", location: "I-16 EB @ MM 8.0", isCMV: false, vehicleTypes: ["Unknown"], liabilitySignals: [], injurySignals: [], scores: { liability: 0.15, injury: 0.0, collectability: 0.1, evidence: 0.15, mechanismSeverity: 0.55, defendantResolution: 0.0, uncertaintyPenalty: 0 }, confidence: { eventCorrelation: 0.5, causalRelationship: 0.3, partyAttribution: 0.05 } }),
  mk({ id: "INC-20391088", label: "Trailer Mechanical Failure", type: "Mechanical Failure", occurredAt: "2025-07-30T09:22:00", location: "I-575 NB @ MM 2.0", isCMV: true, vehicleTypes: ["Box Truck"], liabilitySignals: ["ImproperMaintenance"], injurySignals: [], scores: { liability: 0.55, injury: 0.0, collectability: 0.6, evidence: 0.3, mechanismSeverity: 0.7, defendantResolution: 0.4, uncertaintyPenalty: 0 }, confidence: { eventCorrelation: 0.65, causalRelationship: 0.5, partyAttribution: 0.35 } }),
  mk({ id: "INC-20392201", label: "Wheel-Off Secondary Event", type: "Wheel-Off Incident", occurredAt: "2025-06-05T12:10:00", location: "I-985 NB @ MM 1.0", isCMV: true, vehicleTypes: ["Tractor-Trailer"], liabilitySignals: ["MechanicalFailure"], injurySignals: ["VehicleTowed"], scores: { liability: 0.4, injury: 0.15, collectability: 0.5, evidence: 0.2, mechanismSeverity: 0.85, defendantResolution: 0.1, uncertaintyPenalty: 0.1 }, confidence: { eventCorrelation: 0.6, causalRelationship: 0.4, partyAttribution: 0.15 } }),
  mk({ id: "INC-20393310", label: "Rear-End, Following Too Closely", type: "Rear-End Collision", occurredAt: "2025-09-10T07:45:00", location: "I-575 NB @ MM 2.0", isCMV: false, vehicleTypes: ["Passenger Sedan", "Passenger Truck"], liabilitySignals: ["FollowingTooClosely"], injurySignals: ["ReportedInjury"], scores: { liability: 0.5, injury: 0.3, collectability: 0.15, evidence: 0.3, mechanismSeverity: 0.5, defendantResolution: 0.25, uncertaintyPenalty: 0 }, confidence: { eventCorrelation: 0.7, causalRelationship: 0.55, partyAttribution: 0.3 } }),
  mk({ id: "INC-20394477", label: "Vehicle Stall, Low Priority", type: "Vehicle Stall", occurredAt: "2025-09-25T06:15:00", location: "I-985 NB @ MM 1.0", isCMV: false, vehicleTypes: ["Passenger Sedan"], liabilitySignals: [], injurySignals: [], scores: { liability: 0.05, injury: 0.0, collectability: 0.0, evidence: 0.1, mechanismSeverity: 0.3, defendantResolution: 0.0, uncertaintyPenalty: 0 }, confidence: { eventCorrelation: 0.3, causalRelationship: 0.15, partyAttribution: 0.0 } }),
  mk({ id: "INC-20395522", label: "CMV Rear-End, Strong Signals", type: "Rear-End Collision", occurredAt: "2025-11-15T10:00:00", location: "I-20 WB @ MM 40.0", isCMV: true, vehicleTypes: ["Box Truck", "Passenger Sedan"], liabilitySignals: ["FollowingTooClosely"], injurySignals: ["ReportedInjury", "EMSResponse"], scores: { liability: 0.7, injury: 0.6, collectability: 0.7, evidence: 0.5, mechanismSeverity: 0.5, defendantResolution: 0.5, uncertaintyPenalty: 0 }, confidence: { eventCorrelation: 0.75, causalRelationship: 0.65, partyAttribution: 0.45 } }),
  mk({ id: "INC-20396633", label: "Angle Collision, Evidence Pending", type: "Angle Collision", occurredAt: "2025-11-01T09:00:00", location: "I-20 WB @ MM 5.0", isCMV: true, vehicleTypes: ["Box Truck"], liabilitySignals: ["ImproperLaneChange"], injurySignals: [], scores: { liability: 0.4, injury: 0.0, collectability: 0.5, evidence: 0.15, mechanismSeverity: 0.5, defendantResolution: 0.2, uncertaintyPenalty: 0 }, confidence: { eventCorrelation: 0.55, causalRelationship: 0.35, partyAttribution: 0.2 } }),
  mk({ id: "INC-20397744", label: "Debris Incident, Unresolved", type: "Debris Incident", occurredAt: "2025-12-09T14:10:00", location: "I-75 NB @ MM 10.0", isCMV: false, vehicleTypes: ["Unknown"], liabilitySignals: [], injurySignals: [], scores: { liability: 0.1, injury: 0.0, collectability: 0.0, evidence: 0.1, mechanismSeverity: 0.4, defendantResolution: 0.0, uncertaintyPenalty: 0 }, confidence: { eventCorrelation: 0.35, causalRelationship: 0.2, partyAttribution: 0.0 } }),
  mk({ id: "INC-20398855", label: "Mechanical Failure, Coverage Pending", type: "Mechanical Failure", occurredAt: "2025-12-01T11:00:00", location: "I-75 SB @ MM 12.0", isCMV: true, vehicleTypes: ["Box Truck"], liabilitySignals: ["ImproperMaintenance"], injurySignals: [], scores: { liability: 0.5, injury: 0.0, collectability: 0.5, evidence: 0.3, mechanismSeverity: 0.75, defendantResolution: 0.3, uncertaintyPenalty: 0 }, confidence: { eventCorrelation: 0.6, causalRelationship: 0.45, partyAttribution: 0.25 } }),
];

function computeCOS(scores) {
  const { liability: L, injury: I, collectability: C, evidence: E, mechanismSeverity: M, defendantResolution: D, uncertaintyPenalty: U } = scores;
  const raw = 0.25 * L + 0.20 * I + 0.20 * C + 0.15 * E + 0.10 * M + 0.10 * D - 0.20 * U;
  return Math.max(0, Math.min(1, raw));
}

function hasUnresolvedHighSeverityContradiction(incident) {
  return incident.contradictions.some((c) => c.severity === "high" && !c.resolved);
}

function classifyTier(incident) {
  if (hasUnresolvedHighSeverityContradiction(incident)) return "C";
  const cos = computeCOS(incident.scores);
  if (cos >= 0.80) return "A";
  if (cos >= 0.65) return "B";
  if (cos >= 0.45) return "C";
  return "D";
}

const TIER_LABEL = { A: "Tier A — Priority Investigation", B: "Tier B — High Potential", C: "Tier C — Evidence Development", D: "Tier D — Monitor" };
const TIER_COLOR = { A: "bg-amber-500 text-navy-900", B: "bg-emerald-600 text-white", C: "bg-sky-600 text-white", D: "bg-slate-500 text-white" };

function evidenceCompleteness(incident) {
  const expected = ["Crash Report", "CCTV", "CAD Record", "Tow Record", "EDR", "ELD"];
  const present = new Set(incident.evidence.map((e) => e.type));
  const have = expected.filter((t) => present.has(t)).length;
  return Math.round((have / expected.length) * 100);
}

function isContactEligible(party, overrides) {
  const o = overrides[party.id] || {};
  const legal = o.legalAccessBasis ?? party.legalAccessBasis;
  const solicitation = o.solicitationReview ?? party.solicitationReview;
  const suppression = o.suppressionChecked ?? party.suppressionChecked;
  return legal !== "NotEstablished" && solicitation === "ClearedByCounsel" && suppression === true;
}

const NAV_ITEMS = [
  { id: "dashboard", label: "Executive Dashboard", icon: LayoutDashboard, built: true },
  { id: "pipeline", label: "Case Opportunities", icon: Briefcase, built: true },
  { id: "incidents", label: "Incident Intelligence", icon: FileSearch, built: true },
  { id: "correlation", label: "Correlation Engine", icon: GitBranch, built: false },
  { id: "evidence", label: "Evidence", icon: FileText, built: true },
  { id: "hypotheses", label: "Hypotheses", icon: Lightbulb, built: true },
  { id: "contradictions", label: "Contradictions", icon: AlertTriangle, built: true },
  { id: "parties", label: "Party Resolution", icon: Users, built: true },
  { id: "reports", label: "Reports", icon: BarChart3, built: false },
  { id: "config", label: "System Configuration", icon: Settings, built: false },
];

function ScoreBar({ label, value, accent = "bg-amber-500" }) {
  return <div className="mb-3"><div className="flex justify-between text-xs text-slate-400 mb-1"><span>{label}</span><span className="font-semibold text-slate-200">{Math.round(value * 100)}</span></div><div className="h-2 bg-slate-800 rounded-full overflow-hidden"><div className={`h-full ${accent} rounded-full`} style={{ width: `${value * 100}%` }} /></div></div>;
}
function TierBadge({ tier }) { return <span className={`px-2.5 py-1 rounded text-xs font-bold ${TIER_COLOR[tier]}`}>{TIER_LABEL[tier]}</span>; }
function FactBadge({ status }) { const colors = { "Observed Fact": "bg-emerald-900 text-emerald-300", "Inferred Fact": "bg-sky-900 text-sky-300", "Allegation": "bg-amber-900 text-amber-300", "Model Prediction": "bg-purple-900 text-purple-300", "Attorney Validated Fact": "bg-slate-100 text-slate-900" }; return <span className={`px-2 py-0.5 rounded text-[10px] font-semibold ${colors[status] || "bg-slate-700 text-slate-300"}`}>{status}</span>; }

export default function GCCIApp() {
  const [view, setView] = useState("dashboard");
  const [selectedId, setSelectedId] = useState("PhillipsIncident");
  const [search, setSearch] = useState("");
  const [explainOpen, setExplainOpen] = useState(false);
  const [filters, setFilters] = useState({ cmvOnly: false, minCOS: 0, tier: "ALL" });
  const [complianceOverrides, setComplianceOverrides] = useState({});
  const enriched = useMemo(() => INCIDENTS.map((i) => ({ ...i, cos: computeCOS(i.scores), tier: classifyTier(i), completeness: evidenceCompleteness(i) })), []);
  const selected = enriched.find((i) => i.id === selectedId);
  const searched = useMemo(() => { if (!search.trim()) return enriched; const q = search.toLowerCase(); return enriched.filter((i) => i.id.toLowerCase().includes(q) || i.location.toLowerCase().includes(q) || i.vehicleTypes.some((v) => v.toLowerCase().includes(q)) || i.label.toLowerCase().includes(q)); }, [search, enriched]);
  const filtered = useMemo(() => searched.filter((i) => (!filters.cmvOnly || i.isCMV) && i.cos >= filters.minCOS && (filters.tier === "ALL" || i.tier === filters.tier)), [searched, filters]);
  const kpis = useMemo(() => ({ total: enriched.length, tierA: enriched.filter((i) => i.tier === "A").length, cmv: enriched.filter((i) => i.isCMV).length, avgCOS: Math.round((enriched.reduce((s, i) => s + i.cos, 0) / enriched.length) * 100), gaps: enriched.filter((i) => i.completeness < 50).length, pendingParty: enriched.reduce((s, i) => s + i.parties.filter((p) => p.stage !== "VERIFIED").length, 0) }), [enriched]);
  const tierDist = ["A", "B", "C", "D"].map((t) => ({ tier: t, count: enriched.filter((i) => i.tier === t).length }));
  const goToCase = (id) => { setSelectedId(id); setView("case-detail"); };
  return (
    <div className="flex h-screen bg-slate-950 text-slate-200 font-sans text-sm">
      <aside className="w-60 bg-[#0a1628] border-r border-slate-800 flex flex-col shrink-0">
        <div className="px-5 py-5 border-b border-slate-800"><div className="text-amber-400 font-bold text-lg tracking-tight">G-CCI</div><div className="text-[11px] text-slate-500 mt-0.5">Graham Case Correlation Intelligence</div></div>
        <nav className="flex-1 py-3 overflow-y-auto">{NAV_ITEMS.map((item) => { const Icon = item.icon; const active = view === item.id || (item.id === "pipeline" && view === "case-detail"); return <button key={item.id} onClick={() => setView(item.id)} className={`w-full flex items-center gap-3 px-5 py-2.5 text-left transition ${active ? "bg-amber-500/10 text-amber-400 border-r-2 border-amber-400" : "text-slate-400 hover:bg-slate-800/50 hover:text-slate-200"}`}><Icon size={16}/><span className="flex-1 text-[13px]">{item.label}</span>{!item.built && <span className="text-[9px] px-1.5 py-0.5 bg-slate-800 rounded text-slate-500">SOON</span>}</button>; })}</nav>
        <div className="px-5 py-3 border-t border-slate-800 text-[10px] text-slate-600 leading-relaxed">MVP DEMO — synthetic data only.<br/>No live government, DPPA, law-enforcement, medical, or carrier data is connected.</div>
      </aside>
      <div className="flex-1 flex flex-col overflow-hidden">
        <header className="h-14 border-b border-slate-800 flex items-center px-6 gap-4 bg-[#0a1628]/60 shrink-0"><div className="relative flex-1 max-w-xl"><Search size={15} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500"/><input value={search} onChange={(e)=>setSearch(e.target.value)} placeholder="Search incidents, opportunities, vehicles, carriers, or evidence..." className="w-full bg-slate-900 border border-slate-800 rounded-lg pl-9 pr-3 py-2 text-[13px] placeholder-slate-500 focus:outline-none focus:border-amber-500/50"/></div><div className="text-[11px] text-slate-500">Attorney View · The Graham Firm (demo)</div></header>
        <main className="flex-1 overflow-y-auto p-6">
          {view === "dashboard" && <Dashboard kpis={kpis} tierDist={tierDist} enriched={enriched} goToCase={goToCase}/>} 
          {view === "pipeline" && <Pipeline data={filtered} filters={filters} setFilters={setFilters} goToCase={goToCase}/>} 
          {view === "incidents" && <IncidentRegistry data={searched} goToCase={goToCase}/>} 
          {view === "evidence" && <EvidenceLog data={enriched}/>} 
          {view === "hypotheses" && <HypothesisLog data={enriched} goToCase={goToCase}/>} 
          {view === "contradictions" && <ContradictionCenter data={enriched} goToCase={goToCase}/>} 
          {view === "parties" && <PartyResolution data={enriched} goToCase={goToCase}/>} 
          {view === "case-detail" && selected && <CaseDetail incident={selected} setExplainOpen={setExplainOpen} complianceOverrides={complianceOverrides} setComplianceOverrides={setComplianceOverrides}/>} 
          {(view === "correlation" || view === "reports" || view === "config") && <ComingSoon view={view}/>} 
        </main>
      </div>
      {explainOpen && selected && <ExplainModal incident={selected} onClose={()=>setExplainOpen(false)}/>} 
    </div>
  );
}

function KPICard({label,value,sub}){return <div className="bg-[#0f1f38] border border-slate-800 rounded-xl p-4"><div className="text-[11px] text-slate-500 uppercase tracking-wide mb-1">{label}</div><div className="text-2xl font-bold text-slate-100">{value}</div>{sub&&<div className="text-[11px] text-slate-500 mt-1">{sub}</div>}</div>}
function Dashboard({kpis,tierDist,enriched,goToCase}){const highValue=[...enriched].sort((a,b)=>b.cos-a.cos).slice(0,5);const alerts=enriched.filter((i)=>hasUnresolvedHighSeverityContradiction(i));const COLORS={A:"#f59e0b",B:"#059669",C:"#0284c7",D:"#64748b"};return <div className="space-y-6"><h1 className="text-xl font-bold text-slate-100">Executive Dashboard</h1><div className="grid grid-cols-6 gap-4"><KPICard label="Total Incidents" value={kpis.total}/><KPICard label="High-Priority (Tier A)" value={kpis.tierA}/><KPICard label="CMV Opportunities" value={kpis.cmv}/><KPICard label="Avg. Case Opp. Score" value={`${kpis.avgCOS}`}/><KPICard label="Evidence Gaps" value={kpis.gaps} sub="<50% complete"/><KPICard label="Pending Party Resolution" value={kpis.pendingParty}/></div><div className="grid grid-cols-3 gap-6"><div className="col-span-2 bg-[#0f1f38] border border-slate-800 rounded-xl p-5"><h2 className="text-sm font-semibold text-slate-200 mb-4">Recent High-Value Opportunities</h2><div className="space-y-2">{highValue.map((i)=><button key={i.id} onClick={()=>goToCase(i.id)} className="w-full flex items-center justify-between p-3 bg-slate-900/50 rounded-lg hover:bg-slate-900 text-left"><div><div className="text-[13px] font-medium text-slate-200">{i.label}</div><div className="text-[11px] text-slate-500">{i.location} · {i.type}</div></div><div className="flex items-center gap-3"><TierBadge tier={i.tier}/><span className="text-amber-400 font-bold text-sm">{Math.round(i.cos*100)}</span><ChevronRight size={14} className="text-slate-600"/></div></button>)}</div></div><div className="bg-[#0f1f38] border border-slate-800 rounded-xl p-5"><h2 className="text-sm font-semibold text-slate-200 mb-4">Opportunity Classification Distribution</h2><ResponsiveContainer width="100%" height={180}><BarChart data={tierDist}><CartesianGrid strokeDasharray="3 3" stroke="#1e293b"/><XAxis dataKey="tier" stroke="#64748b" fontSize={11}/><YAxis stroke="#64748b" fontSize={11} allowDecimals={false}/><Tooltip contentStyle={{background:"#0f1f38",border:"1px solid #334155",fontSize:12}}/><Bar dataKey="count" radius={[4,4,0,0]}>{tierDist.map((d)=><Cell key={d.tier} fill={COLORS[d.tier]}/>)}</Bar></BarChart></ResponsiveContainer><div className="mt-4 pt-4 border-t border-slate-800"><h3 className="text-[11px] uppercase text-slate-500 mb-2">Alerts Requiring Attorney Review</h3>{alerts.length===0&&<div className="text-[12px] text-slate-500">No unresolved high-severity contradictions.</div>}{alerts.map((i)=><button key={i.id} onClick={()=>goToCase(i.id)} className="w-full flex items-center gap-2 text-left text-[12px] text-amber-400 py-1 hover:text-amber-300"><AlertTriangle size={13}/>{i.label} — contradiction blocking Tier A</button>)}</div></div></div></div>}
function Pipeline({data,filters,setFilters,goToCase}){return <div className="space-y-5"><h1 className="text-xl font-bold text-slate-100">Case Opportunity Pipeline</h1><div className="flex items-center gap-4 bg-[#0f1f38] border border-slate-800 rounded-xl p-4"><label className="flex items-center gap-2 text-[12px]"><input type="checkbox" checked={filters.cmvOnly} onChange={(e)=>setFilters((f)=>({...f,cmvOnly:e.target.checked}))}/>Commercial Motor Vehicle Only</label><label className="flex items-center gap-2 text-[12px]">Min Case Opp. Score<input type="range" min="0" max="1" step="0.05" value={filters.minCOS} onChange={(e)=>setFilters((f)=>({...f,minCOS:parseFloat(e.target.value)}))}/><span className="text-amber-400 font-semibold">{Math.round(filters.minCOS*100)}</span></label><label className="flex items-center gap-2 text-[12px]">Tier<select value={filters.tier} onChange={(e)=>setFilters((f)=>({...f,tier:e.target.value}))} className="bg-slate-900 border border-slate-700 rounded px-2 py-1"><option value="ALL">All</option><option value="A">A</option><option value="B">B</option><option value="C">C</option><option value="D">D</option></select></label><span className="ml-auto text-[12px] text-slate-500">{data.length} results</span></div><div className="grid grid-cols-2 gap-4">{data.map((i)=><button key={i.id} onClick={()=>goToCase(i.id)} className="text-left bg-[#0f1f38] border border-slate-800 rounded-xl p-4 hover:border-amber-500/40 transition"><div className="flex justify-between items-start mb-2"><div><div className="font-semibold text-slate-100 text-[14px]">{i.label}</div><div className="text-[11px] text-slate-500">{i.id} · {new Date(i.occurredAt).toLocaleString()}</div></div><TierBadge tier={i.tier}/></div><div className="text-[12px] text-slate-400 mb-2">{i.location} · {i.type} {i.isCMV&&<span className="text-amber-400 font-semibold">· CMV</span>}</div><div className="flex flex-wrap gap-1 mb-3">{i.liabilitySignals.map((s)=><span key={s} className="text-[10px] px-1.5 py-0.5 bg-slate-800 rounded text-slate-300">{s}</span>)}{i.injurySignals.map((s)=><span key={s} className="text-[10px] px-1.5 py-0.5 bg-rose-950 text-rose-300 rounded">{s}</span>)}</div><div className="grid grid-cols-3 gap-2 text-[11px] text-slate-500 mb-2"><div>Correlation<div className="text-slate-200 font-semibold">{Math.round(i.confidence.eventCorrelation*100)}</div></div><div>Causal<div className="text-slate-200 font-semibold">{Math.round(i.confidence.causalRelationship*100)}</div></div><div>Attribution<div className="text-slate-200 font-semibold">{Math.round(i.confidence.partyAttribution*100)}</div></div></div><div className="flex justify-between items-center pt-2 border-t border-slate-800"><span className="text-[11px] text-slate-500">Evidence {i.completeness}% · Party {i.parties.length?i.parties[0].stage:"N/A"}</span><span className="text-lg font-bold text-amber-400">{Math.round(i.cos*100)}</span></div></button>)}</div></div>}
function IncidentRegistry({data,goToCase}){return <div className="space-y-4"><h1 className="text-xl font-bold text-slate-100">Incident Intelligence</h1><p className="text-[12px] text-slate-500">Raw normalized incidents, prior to case-opportunity qualification. "What happened," not "is this a lead."</p><table className="w-full text-[12px] bg-[#0f1f38] border border-slate-800 rounded-xl overflow-hidden"><thead className="bg-slate-900 text-slate-500 uppercase text-[10px]"><tr><th className="text-left p-3">Incident</th><th className="text-left p-3">Type</th><th className="text-left p-3">Location</th><th className="text-left p-3">Vehicles</th><th className="text-left p-3">Occurred</th><th></th></tr></thead><tbody>{data.map((i)=><tr key={i.id} className="border-t border-slate-800 hover:bg-slate-900/50 cursor-pointer" onClick={()=>goToCase(i.id)}><td className="p-3 text-slate-200">{i.id}</td><td className="p-3 text-slate-400">{i.type}</td><td className="p-3 text-slate-400">{i.location}</td><td className="p-3 text-slate-400">{i.vehicleTypes.join(", ")}</td><td className="p-3 text-slate-400">{new Date(i.occurredAt).toLocaleDateString()}</td><td className="p-3"><ChevronRight size={14} className="text-slate-600"/></td></tr>)}</tbody></table></div>}
function EvidenceLog({data}){const rows=data.flatMap((i)=>i.evidence.map((e)=>({...e,incidentId:i.id,incidentLabel:i.label})));return <div className="space-y-4"><h1 className="text-xl font-bold text-slate-100">Evidence Log</h1><div className="bg-[#0f1f38] border border-slate-800 rounded-xl overflow-hidden"><table className="w-full text-[12px]"><thead className="bg-slate-900 text-slate-500 uppercase text-[10px]"><tr><th className="text-left p-3">Incident</th><th className="text-left p-3">Type</th><th className="text-left p-3">Source</th><th className="text-left p-3">Timestamp</th><th className="text-left p-3">Fact Status</th><th className="text-left p-3">Provenance</th></tr></thead><tbody>{rows.map((e)=><tr key={e.id} className="border-t border-slate-800"><td className="p-3 text-slate-300">{e.incidentLabel}</td><td className="p-3 text-slate-400">{e.type}</td><td className="p-3 text-slate-400">{e.source}</td><td className="p-3 text-slate-500">{new Date(e.timestamp).toLocaleString()}</td><td className="p-3"><FactBadge status={e.factStatus}/></td><td className="p-3 text-slate-500">{e.provenance}</td></tr>)}</tbody></table></div></div>}
function HypothesisLog({data,goToCase}){const rows=data.flatMap((i)=>i.hypotheses.map((h)=>({...h,incidentId:i.id,incidentLabel:i.label})));return <div className="space-y-4"><h1 className="text-xl font-bold text-slate-100">Hypothesis Engine</h1><div className="space-y-3">{rows.map((h)=><div key={h.id} className="bg-[#0f1f38] border border-slate-800 rounded-xl p-4"><div className="flex justify-between items-start mb-2"><div><button onClick={()=>goToCase(h.incidentId)} className="text-[12px] text-amber-400 hover:underline">{h.incidentLabel}</button><div className="text-[13px] text-slate-200 mt-1">{h.description}</div></div><div className="text-right shrink-0 ml-4"><div className="text-[10px] text-slate-500">Machine Confidence</div><div className="text-lg font-bold text-slate-100">{Math.round(h.confidence*100)}</div></div></div></div>)}</div></div>}
function ContradictionCenter({data,goToCase}){const rows=data.flatMap((i)=>i.contradictions.map((c)=>({...c,incidentId:i.id,incidentLabel:i.label})));return <div className="space-y-4"><h1 className="text-xl font-bold text-slate-100">Contradiction Center</h1>{rows.map((c)=><div key={c.id} className="bg-rose-950/30 border border-rose-800 rounded-xl p-4"><div className="flex justify-between items-center mb-3"><span className="text-[11px] font-bold uppercase text-rose-400">{c.severity}-Severity Contradiction</span><button onClick={()=>goToCase(c.incidentId)} className="text-[12px] text-amber-400 hover:underline">{c.incidentLabel}</button></div><div className="grid grid-cols-2 gap-3 text-[12px]"><div className="bg-slate-900/60 rounded p-2">{c.assertionA}</div><div className="bg-slate-900/60 rounded p-2">{c.assertionB}</div></div></div>)}</div>}
function PartyResolution({data,goToCase}){const rows=data.flatMap((i)=>i.parties.map((p)=>({...p,incidentId:i.id,incidentLabel:i.label})));return <div className="space-y-4"><h1 className="text-xl font-bold text-slate-100">Party Resolution</h1><table className="w-full text-[12px] bg-[#0f1f38] border border-slate-800 rounded-xl overflow-hidden"><tbody>{rows.map((p)=><tr key={p.id} className="border-t border-slate-800"><td className="p-3"><button onClick={()=>goToCase(p.incidentId)} className="text-amber-400 hover:underline">{p.incidentLabel}</button></td><td className="p-3 text-slate-300">{p.role}</td><td className="p-3 text-slate-400">{p.stage}</td><td className="p-3 text-slate-500">{p.note}</td></tr>)}</tbody></table></div>}
function ComingSoon({view}){const labels={correlation:"Correlation Engine (interactive relationship graph)",reports:"Reports",config:"System Configuration"};return <div className="flex flex-col items-center justify-center h-full text-center"><Info size={32} className="text-slate-600 mb-3"/><div className="text-slate-300 font-semibold mb-1">{labels[view]} — not yet built in this MVP pass</div></div>}
function CaseDetail({incident,setExplainOpen,complianceOverrides,setComplianceOverrides}){const [tab,setTab]=useState("overview");const setOverride=(partyId,field,value)=>setComplianceOverrides((prev)=>({...prev,[partyId]:{...prev[partyId],[field]:value}}));return <div className="space-y-5"><div className="flex justify-between items-start"><div><div className="text-[11px] text-amber-400 uppercase tracking-wide font-semibold mb-1">Case Opportunity</div><h1 className="text-xl font-bold text-slate-100">{incident.label}</h1><div className="text-[12px] text-slate-500 mt-1">Opportunity ID: opp_{incident.id} · Incident ID: {incident.id}</div></div><div className="text-right"><TierBadge tier={incident.tier}/><div className="text-3xl font-bold text-amber-400 mt-2">{Math.round(incident.cos*100)}</div><button onClick={()=>setExplainOpen(true)} className="mt-2 text-[12px] px-3 py-1.5 bg-amber-500 text-slate-900 font-semibold rounded-lg hover:bg-amber-400">Explain This Decision</button></div></div><div className="flex gap-1 border-b border-slate-800">{["overview","evidence","hypotheses","contradictions","parties"].map((t)=><button key={t} onClick={()=>setTab(t)} className={`px-4 py-2 text-[12px] font-medium capitalize ${tab===t?"text-amber-400 border-b-2 border-amber-400":"text-slate-500 hover:text-slate-300"}`}>{t}</button>)}</div>{tab==="overview"&&<div className="grid grid-cols-2 gap-6"><div className="bg-[#0f1f38] border border-slate-800 rounded-xl p-5"><ScoreBar label="Liability" value={incident.scores.liability}/><ScoreBar label="Injury" value={incident.scores.injury}/><ScoreBar label="Collectability" value={incident.scores.collectability}/><ScoreBar label="Evidence" value={incident.scores.evidence}/><ScoreBar label="Mechanism Severity" value={incident.scores.mechanismSeverity}/><ScoreBar label="Defendant Resolution" value={incident.scores.defendantResolution}/></div><div className="bg-[#0f1f38] border border-amber-900/40 rounded-xl p-5"><h2 className="text-sm font-semibold text-slate-200 mb-4">Three Separate Confidence Measures</h2>{[["Event Correlation",incident.confidence.eventCorrelation],["Causal Relationship",incident.confidence.causalRelationship],["Party Attribution",incident.confidence.partyAttribution]].map(([l,v])=><div key={l} className="bg-slate-900/60 rounded-lg p-3 mb-3"><div className="text-[10px] uppercase text-sky-400 font-bold mb-1">{l}</div><div className="text-2xl font-bold text-slate-100">{Math.round(v*100)}</div></div>)}</div></div>}{tab==="evidence"&&<EvidenceLog data={[incident]}/>} {tab==="hypotheses"&&<HypothesisLog data={[incident]} goToCase={()=>{}}/>} {tab==="contradictions"&&<ContradictionCenter data={[incident]} goToCase={()=>{}}/>} {tab==="parties"&&<div className="space-y-3">{incident.parties.map((p)=>{const eligible=isContactEligible(p,complianceOverrides);const o=complianceOverrides[p.id]||{};return <div key={p.id} className="bg-[#0f1f38] border border-slate-800 rounded-xl p-4"><div className="flex justify-between items-start mb-3"><div><div className="text-slate-200 font-medium text-[13px]">{p.role}</div><div className="text-[11px] text-slate-500">{p.note}</div></div><span className={`px-2.5 py-1 rounded text-[11px] font-bold ${eligible?"bg-emerald-700 text-white":"bg-slate-700 text-slate-300"}`}>{eligible?"CONTACT ELIGIBLE":"Not Contact Eligible"}</span></div><div className="grid grid-cols-3 gap-3 text-[11px]"><label>Legal Access Basis<select value={o.legalAccessBasis??p.legalAccessBasis} onChange={(e)=>setOverride(p.id,"legalAccessBasis",e.target.value)} className="w-full mt-1 bg-slate-900 border border-slate-700 rounded px-2 py-1"><option value="NotEstablished">Not Established</option><option value="PublicRecord">Public Record</option><option value="OpenRecordsRequest">Open Records Request</option><option value="ClientProvided">Client Provided</option></select></label><label>Solicitation Review<select value={o.solicitationReview??p.solicitationReview} onChange={(e)=>setOverride(p.id,"solicitationReview",e.target.value)} className="w-full mt-1 bg-slate-900 border border-slate-700 rounded px-2 py-1"><option value="NotReviewed">Not Reviewed</option><option value="WithinHoldPeriod">Within Hold Period</option><option value="ClearedByCounsel">Cleared By Counsel</option><option value="RejectedByCounsel">Rejected By Counsel</option></select></label><label className="flex items-center gap-2 self-end pb-1"><input type="checkbox" checked={o.suppressionChecked??p.suppressionChecked} onChange={(e)=>setOverride(p.id,"suppressionChecked",e.target.checked)}/> Suppression Checked</label></div></div>})}</div>}</div>}
function ExplainModal({incident,onClose}){const missing=["Crash Report","CCTV","CAD Record","Tow Record","EDR","ELD"].filter((t)=>!incident.evidence.some((e)=>e.type===t));return <div className="fixed inset-0 bg-black/70 flex items-center justify-center z-50 p-6" onClick={onClose}><div className="bg-[#0f1f38] border border-slate-700 rounded-2xl max-w-2xl w-full max-h-[85vh] overflow-y-auto" onClick={(e)=>e.stopPropagation()}><div className="flex justify-between items-center p-5 border-b border-slate-800"><h2 className="font-bold text-slate-100">Explain This Decision — {incident.label}</h2><button onClick={onClose}><X size={18} className="text-slate-500 hover:text-slate-300"/></button></div><div className="p-5 space-y-4 text-[13px]"><p className="text-slate-300">Case Opportunity Score of {Math.round(incident.cos*100)} computed from weighted liability, injury, collectability, evidence, mechanism severity, defendant resolution, and uncertainty penalty.</p><div><div className="text-[11px] uppercase text-sky-400 font-semibold mb-1">Missing Evidence</div><div className="flex flex-wrap gap-1">{missing.map((m)=><span key={m} className="text-[11px] px-2 py-0.5 bg-slate-800 rounded text-slate-400">{m}</span>)}</div></div><div><div className="text-[11px] uppercase text-amber-400 font-semibold mb-1">Recommended Next Actions</div><ul className="list-disc list-inside text-slate-300 space-y-0.5">{missing.slice(0,3).map((m)=><li key={m}>Obtain {m}</li>)}{incident.contradictions.some((c)=>!c.resolved)&&<li>Resolve unresolved contradiction before Tier A eligibility</li>}<li>Attorney review of compiled findings</li></ul></div></div></div></div>}
