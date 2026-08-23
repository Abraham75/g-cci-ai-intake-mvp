import React, { useEffect, useMemo, useState } from "react";
import {
  AlertTriangle,
  ArrowLeft,
  Camera,
  CheckCircle2,
  Clock3,
  GitBranch,
  MapPin,
  RefreshCw,
  Scale,
  ShieldCheck,
  Target,
} from "lucide-react";
import { gcciApi } from "./api.js";

const TABS = [
  ["overview", "Overview"],
  ["cameras", "Map & Cameras"],
  ["acquisition", "Evidence Acquisition"],
  ["revisions", "Revision History"],
  ["ledger", "Provenance / Ledger"],
  ["boundaries", "Parties & Compliance"],
];

const TIER_STYLE = {
  A: "bg-amber-500 text-slate-950",
  B: "bg-emerald-600 text-white",
  C: "bg-sky-600 text-white",
  D: "bg-slate-600 text-white",
};

function pick(object, ...names) {
  for (const name of names) {
    if (object && object[name] !== undefined && object[name] !== null) return object[name];
  }
  return undefined;
}

function pct(value) {
  return typeof value === "number" ? `${Math.round(value * 100)}%` : "—";
}

function dateTime(value) {
  if (!value) return "—";
  const parsed = new Date(value);
  return Number.isNaN(parsed.getTime()) ? String(value) : parsed.toLocaleString();
}

export default function CaseIntelligenceDetail({ hypothesisId, onBack }) {
  const [tab, setTab] = useState("overview");
  const [state, setState] = useState({
    hypothesis: null,
    revisions: [],
    currentScore: null,
    scoreHistory: [],
    tasks: [],
    cameras: [],
    cameraStatus: null,
    ledger: [],
    ledgerIntegrity: null,
  });
  const [loading, setLoading] = useState(false);
  const [cameraRefreshing, setCameraRefreshing] = useState(false);
  const [error, setError] = useState("");

  const load = async () => {
    if (!hypothesisId) return;
    setLoading(true);
    setError("");
    try {
      const [hypothesis, revisions, currentScore, scoreHistory, tasks, cameras, cameraStatus, ledger, ledgerIntegrity] =
        await Promise.all([
          gcciApi.hypothesis(hypothesisId),
          gcciApi.hypothesisRevisions(hypothesisId),
          gcciApi.currentScore(hypothesisId),
          gcciApi.scoreHistory(hypothesisId),
          gcciApi.acquisitionTasks(hypothesisId),
          gcciApi.hypothesisCameras(hypothesisId),
          gcciApi.cameraStatus(),
          gcciApi.subjectLedger(hypothesisId),
          gcciApi.persistentLedgerIntegrity(),
        ]);
      setState({ hypothesis, revisions, currentScore, scoreHistory, tasks, cameras, cameraStatus, ledger, ledgerIntegrity });
    } catch (e) {
      setError(e instanceof Error ? e.message : "Unknown case-intelligence error");
    } finally {
      setLoading(false);
    }
  };

  const refreshCameras = async () => {
    if (!hypothesisId) return;
    setCameraRefreshing(true);
    setError("");
    try {
      await gcciApi.refreshHypothesisCameras(hypothesisId);
      const [cameras, cameraStatus, ledger] = await Promise.all([
        gcciApi.hypothesisCameras(hypothesisId),
        gcciApi.cameraStatus(),
        gcciApi.subjectLedger(hypothesisId),
      ]);
      setState((s) => ({ ...s, cameras, cameraStatus, ledger }));
    } catch (e) {
      setError(e instanceof Error ? e.message : "Camera refresh failed");
    } finally {
      setCameraRefreshing(false);
    }
  };

  useEffect(() => {
    load();
  }, [hypothesisId]);

  const vm = useMemo(() => buildViewModel(state, hypothesisId), [state, hypothesisId]);

  if (!hypothesisId) {
    return <EmptyState title="No IncidentHypothesis selected" text="Open a persisted correlated incident to enter Case Intelligence Detail." />;
  }

  return (
    <div className="space-y-6">
      <div className="flex items-start justify-between gap-4">
        <div className="flex items-start gap-3">
          {onBack && (
            <button onClick={onBack} className="mt-1 p-2 rounded-lg bg-slate-900 border border-slate-800 hover:bg-slate-800" aria-label="Back">
              <ArrowLeft size={15} />
            </button>
          )}
          <div>
            <div className="text-[10px] uppercase tracking-[0.18em] text-amber-400 font-bold">Case Intelligence Detail</div>
            <h1 className="text-2xl font-bold text-slate-100 mt-1">{vm.title}</h1>
            <div className="text-[11px] text-slate-500 mt-1">{hypothesisId} · Revision {vm.revision} · {vm.location}</div>
          </div>
        </div>
        <button onClick={load} disabled={loading} className="flex items-center gap-2 px-3 py-2 bg-slate-800 rounded-lg text-xs hover:bg-slate-700 disabled:opacity-50">
          <RefreshCw size={13} className={loading ? "animate-spin" : ""} /> Refresh case
        </button>
      </div>

      {error && <div className="border border-rose-800 bg-rose-950/30 text-rose-300 rounded-xl p-4 text-sm">{error}</div>}

      <CaseHeader vm={vm} />
      <ConfidenceStrip vm={vm} />

      <div className="flex gap-1 border-b border-slate-800 overflow-x-auto">
        {TABS.map(([id, label]) => (
          <button key={id} onClick={() => setTab(id)} className={`px-4 py-2.5 whitespace-nowrap text-xs ${tab === id ? "text-amber-400 border-b-2 border-amber-400" : "text-slate-500 hover:text-slate-300"}`}>
            {label}
          </button>
        ))}
      </div>

      {loading && !state.hypothesis ? <LoadingState /> : null}
      {!loading || state.hypothesis ? (
        <>
          {tab === "overview" && <Overview vm={vm} />}
          {tab === "cameras" && (
            <CameraWorkspace
              hypothesis={state.hypothesis}
              cameras={state.cameras}
              cameraStatus={state.cameraStatus}
              refreshing={cameraRefreshing}
              onRefresh={refreshCameras}
            />
          )}
          {tab === "acquisition" && <AcquisitionPanel tasks={state.tasks} cameras={state.cameras} />}
          {tab === "revisions" && <RevisionPanel revisions={state.revisions} scoreHistory={state.scoreHistory} />}
          {tab === "ledger" && <LedgerPanel entries={state.ledger} integrity={state.ledgerIntegrity} />}
          {tab === "boundaries" && <IntegrationBoundary />}
        </>
      ) : null}
    </div>
  );
}

function buildViewModel(state, hypothesisId) {
  const h = state.hypothesis || {};
  const currentScoreEnvelope = state.currentScore || {};
  const score = currentScoreEnvelope.latestScore || {};
  const confidence = score.confidence || {};
  const memberIds = pick(h, "member_event_ids", "memberEventIds") || [];
  const contradictions = pick(h, "contradictions") || [];
  const rationale = pick(h, "rationale") || [];
  const tier = score.tier || state.scoreHistory.at(-1)?.tier || "—";
  const scoreValue = typeof score.score === "number" ? score.score : state.scoreHistory.at(-1)?.score;
  const roadway = pick(h, "roadway") || "Roadway unresolved";
  const direction = pick(h, "direction");
  const revision = currentScoreEnvelope.currentHypothesisRevision || state.revisions.length || "—";
  const classification = pick(h, "classification") || "unclassified";
  const machineConfidence = pick(h, "machine_confidence", "machineConfidence");
  const latestScoredRevision = currentScoreEnvelope.latestScoredRevision;
  const staleScore = typeof latestScoredRevision === "number" && typeof revision === "number" && latestScoredRevision < revision;

  return {
    hypothesisId,
    title: `${roadway}${direction ? ` ${direction}` : ""} — ${classification.replaceAll("_", " ")}`,
    revision,
    location: `${roadway}${direction ? ` ${direction}` : ""}`,
    classification,
    status: pick(h, "status") || "MachineProposed",
    modelVersion: pick(h, "model_version", "modelVersion") || "—",
    startTime: pick(h, "start_time", "startTime"),
    endTime: pick(h, "end_time", "endTime"),
    memberIds,
    contradictions,
    rationale,
    tier,
    score: scoreValue,
    scoreModelVersion: score.modelVersion || state.scoreHistory.at(-1)?.modelVersion || "—",
    scoreReasons: score.reasons || [],
    eventCorrelation: confidence.eventCorrelation ?? machineConfidence,
    causalRelationship: confidence.causalRelationship,
    partyAttribution: confidence.partyAttribution,
    contactEligibility: "NOT_EVALUATED",
    pendingScoreJob: currentScoreEnvelope.pendingScoreJob,
    latestScoredRevision,
    staleScore,
    scoreAvailable: typeof scoreValue === "number",
  };
}

function CaseHeader({ vm }) {
  return (
    <div className="bg-[#0f1f38] border border-slate-800 rounded-2xl p-5">
      <div className="flex flex-col lg:flex-row lg:items-start justify-between gap-5">
        <div>
          <div className="flex flex-wrap gap-2">
            <Badge text={vm.classification.replaceAll("_", " ")} />
            <Badge text={vm.status} />
            <Badge text={`${vm.memberIds.length} supporting records`} />
            {vm.contradictions.length > 0 && <Badge text={`${vm.contradictions.length} contradiction(s)`} danger />}
          </div>
          <div className="grid md:grid-cols-3 gap-4 mt-5 text-xs">
            <Meta icon={Clock3} label="Evidence window" value={`${dateTime(vm.startTime)} → ${dateTime(vm.endTime)}`} />
            <Meta icon={GitBranch} label="Correlation model" value={vm.modelVersion} />
            <Meta icon={Target} label="Canonical scoring model" value={vm.scoreModelVersion} />
          </div>
        </div>
        <div className="flex items-center gap-5 lg:text-right">
          <div><div className="text-[10px] uppercase text-slate-500">Case Opportunity Score</div><div className="text-4xl font-bold text-amber-400">{vm.scoreAvailable ? Math.round(vm.score * 100) : "—"}</div></div>
          <span className={`px-3 py-2 rounded text-xs font-bold ${TIER_STYLE[vm.tier] || "bg-slate-800 text-slate-400"}`}>TIER {vm.tier}</span>
        </div>
      </div>
      {vm.staleScore && <Warning>Hypothesis Revision {vm.revision} is newer than the latest completed score (Revision {vm.latestScoredRevision}).</Warning>}
      {vm.pendingScoreJob && <div className="mt-3 text-[11px] text-slate-500">Score job Revision {vm.pendingScoreJob.revision}: {vm.pendingScoreJob.status} · attempts {vm.pendingScoreJob.attempts}</div>}
    </div>
  );
}

function ConfidenceStrip({ vm }) {
  const items = [
    ["Event Correlation", vm.eventCorrelation, "Do the source records describe the same event sequence?", "text-sky-400"],
    ["Causal Relationship", vm.causalRelationship, "Did one event materially cause or contribute to another?", "text-emerald-400"],
    ["Party Attribution", vm.partyAttribution, "Can responsibility be tied to a specific party?", "text-rose-400"],
  ];
  return (
    <div className="grid md:grid-cols-4 gap-4">
      {items.map(([label, value, help, color]) => <MetricCard key={label} label={label} value={pct(value)} help={help} color={color} />)}
      <MetricCard label="Contact Eligibility" value={vm.contactEligibility} help="Independent compliance review required; never inferred from case analytics." color="text-rose-400" />
    </div>
  );
}

function Overview({ vm }) {
  return (
    <div className="grid lg:grid-cols-3 gap-6">
      <Panel title="Attorney Executive Assessment" className="lg:col-span-2">
        <Section title="Current machine hypothesis">G-CCI classifies this cluster as <strong>{vm.classification.replaceAll("_", " ")}</strong> with event-connection confidence of <strong>{pct(vm.eventCorrelation)}</strong>. This is an analytical hypothesis, not a party-liability finding.</Section>
        <Section title="Why the system connected these records">{vm.rationale.length ? <BulletList items={vm.rationale} /> : <Muted>No rationale persisted on this revision.</Muted>}</Section>
        <Section title="Material contradictions">{vm.contradictions.length ? <BulletList items={vm.contradictions.map(String)} danger /> : <div className="flex items-center gap-2 text-emerald-400 text-xs"><CheckCircle2 size={14} />No contradiction persisted on the current revision.</div>}</Section>
        <Section title="Canonical score reasoning">{vm.scoreReasons.length ? <BulletList items={vm.scoreReasons} /> : <Muted>No canonical score reasons available yet.</Muted>}</Section>
      </Panel>
      <Panel title="Current Decision State">
        <DecisionRow label="Hypothesis Revision" value={String(vm.revision)} />
        <DecisionRow label="Supporting Records" value={String(vm.memberIds.length)} />
        <DecisionRow label="Latest Scored Revision" value={vm.latestScoredRevision ?? "—"} />
        <DecisionRow label="COS / Tier" value={vm.scoreAvailable ? `${Math.round(vm.score * 100)} / ${vm.tier}` : "Pending"} />
        <DecisionRow label="Contact Eligibility" value="NOT_EVALUATED" danger />
        <div className="mt-5 p-3 rounded-lg bg-slate-900/60 text-[11px] text-slate-500 leading-relaxed"><Scale size={14} className="text-amber-400 mb-2" />Correlation, causation, attribution, economics, camera relevance, and contact permission remain separate.</div>
      </Panel>
    </div>
  );
}

function CameraWorkspace({ hypothesis, cameras, cameraStatus, refreshing, onRefresh }) {
  const centroid = pick(hypothesis, "centroid") || null;
  const current = cameras.filter((c) => c.status === "CURRENT");
  return (
    <div className="space-y-5">
      <div className="flex items-center justify-between gap-4">
        <div><div className="text-sm font-semibold">Persistent Camera Intelligence</div><div className="text-[11px] text-slate-500 mt-1">PostGIS distance plus roadway and direction compatibility. Camera relevance is evidence-discovery intelligence only.</div></div>
        <button onClick={onRefresh} disabled={refreshing} className="flex items-center gap-2 px-3 py-2 bg-slate-800 rounded-lg text-xs hover:bg-slate-700 disabled:opacity-50"><RefreshCw size={13} className={refreshing ? "animate-spin" : ""}/>Recompute cameras</button>
      </div>
      <div className="grid md:grid-cols-3 gap-4">
        <MetricCard label="Active Camera Inventory" value={cameraStatus?.activeCameraCount ?? "—"} help={`Last inventory observation: ${dateTime(cameraStatus?.lastSeenAt)}`} color="text-sky-400" />
        <MetricCard label="Current Candidates" value={current.length} help="Bound to the current hypothesis revision." color="text-emerald-400" />
        <MetricCard label="Best Camera Relevance" value={current.length ? pct(Math.max(...current.map((c) => c.relevanceScore))) : "—"} help="Distance + roadway + direction only." color="text-amber-400" />
      </div>
      <div className="grid lg:grid-cols-2 gap-6">
        <Panel title="Spatial Investigation View"><SpatialCanvas centroid={centroid} cameras={current} /></Panel>
        <Panel title="Nearest Relevant Cameras"><CameraList cameras={current} /></Panel>
      </div>
    </div>
  );
}

function SpatialCanvas({ centroid, cameras }) {
  if (!centroid || typeof centroid.latitude !== "number" || typeof centroid.longitude !== "number") return <EmptyState title="No hypothesis centroid" text="Camera geometry cannot be visualized until the hypothesis has a persisted centroid." />;
  const points = [{ id: "incident", latitude: centroid.latitude, longitude: centroid.longitude, incident: true }, ...cameras];
  const lats = points.map((p) => p.latitude); const lons = points.map((p) => p.longitude);
  const minLat = Math.min(...lats); const maxLat = Math.max(...lats); const minLon = Math.min(...lons); const maxLon = Math.max(...lons);
  const latSpan = Math.max(maxLat - minLat, 0.002); const lonSpan = Math.max(maxLon - minLon, 0.002);
  const position = (p) => ({ left: `${8 + 84 * ((p.longitude - minLon) / lonSpan)}%`, top: `${8 + 84 * (1 - (p.latitude - minLat) / latSpan)}%` });
  return (
    <div className="relative h-[420px] rounded-xl overflow-hidden bg-slate-950 border border-slate-800">
      <div className="absolute inset-0 opacity-30" style={{ backgroundImage: "linear-gradient(#334155 1px,transparent 1px),linear-gradient(90deg,#334155 1px,transparent 1px)", backgroundSize: "32px 32px" }} />
      <div className="absolute left-4 top-4 text-[10px] text-slate-500">Dependency-free geospatial preview · replaceable with MapLibre without changing API</div>
      {points.map((p) => <div key={p.id || p.cameraId} className="absolute -translate-x-1/2 -translate-y-1/2 group" style={position(p)}>
        <div className={`w-4 h-4 rounded-full border-2 ${p.incident ? "bg-amber-500 border-amber-200 shadow-[0_0_18px_rgba(245,158,11,.8)]" : "bg-sky-500 border-sky-200"}`} />
        <div className="hidden group-hover:block absolute z-10 left-5 top-0 min-w-44 bg-slate-900 border border-slate-700 rounded p-2 text-[10px] shadow-xl">{p.incident ? "IncidentHypothesis centroid" : `${p.name} · ${Math.round(p.distanceMeters)} m · ${pct(p.relevanceScore)}`}</div>
      </div>)}
      <div className="absolute bottom-4 left-4 flex gap-4 text-[10px] text-slate-500"><span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-amber-500"/>Hypothesis</span><span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-sky-500"/>Camera</span></div>
    </div>
  );
}

function CameraList({ cameras }) {
  if (!cameras.length) return <Muted>No current camera candidates are persisted. Ingest the camera inventory, then recompute this hypothesis.</Muted>;
  return <div className="space-y-3">{cameras.map((c, index) => <div key={c.id} className="bg-slate-900/60 border border-slate-800 rounded-xl p-4">
    <div className="flex items-start justify-between gap-4"><div><div className="flex items-center gap-2"><Camera size={14} className="text-sky-400"/><span className="font-semibold text-sm">{index + 1}. {c.name}</span></div><div className="text-[10px] text-slate-500 mt-1">{c.cameraId} · {Math.round(c.distanceMeters)} m · {c.roadway || "roadway unknown"} {c.direction || ""}</div></div><div className="text-right"><div className="text-2xl font-bold text-amber-400">{pct(c.relevanceScore)}</div><div className="text-[9px] text-slate-600">relevance</div></div></div>
    <div className="grid grid-cols-3 gap-2 mt-3"><Mini label="Roadway" value={c.roadwayMatch ? "MATCH" : "NO MATCH"}/><Mini label="Direction" value={c.directionMatch ? "MATCH" : "NO/UNKNOWN"}/><Mini label="Status" value={c.status}/></div>
    <div className="mt-3 p-3 rounded-lg bg-amber-500/10 border border-amber-800/30"><div className="text-[9px] uppercase font-bold text-amber-400">Preservation Window</div><div className="text-[11px] mt-1">{dateTime(c.preservationWindowStart)} → {dateTime(c.preservationWindowEnd)}</div></div>
    {(c.snapshotUrl || c.streamUrl) && <div className="mt-3 flex gap-2">{c.snapshotUrl && <a href={c.snapshotUrl} target="_blank" rel="noreferrer" className="text-[10px] px-2 py-1 rounded bg-sky-900/50 text-sky-300">Snapshot source</a>}{c.streamUrl && <a href={c.streamUrl} target="_blank" rel="noreferrer" className="text-[10px] px-2 py-1 rounded bg-sky-900/50 text-sky-300">Stream source</a>}</div>}
  </div>)}</div>;
}

function AcquisitionPanel({ tasks, cameras }) {
  const sorted = [...tasks].sort((a, b) => (b.acquisitionPriorityScore || 0) - (a.acquisitionPriorityScore || 0));
  const bestCamera = [...cameras].sort((a, b) => (b.relevanceScore || 0) - (a.relevanceScore || 0))[0];
  return <Panel title="Evidence Acquisition Queue"><p className="text-[11px] text-slate-500 mb-4">Camera tasks are enriched with the best persisted camera candidate when one exists.</p>{!sorted.length ? <Muted>No acquisition tasks generated.</Muted> : <div className="space-y-3">{sorted.map((task) => <div key={task.id} className="bg-slate-900/60 rounded-lg p-4 border border-slate-800"><div className="flex justify-between"><div><div className="font-semibold text-sm">{task.evidenceType}</div><div className="text-[11px] text-slate-500 mt-1">Revision {task.revision} · EIG {Number(task.expectedInformationGain || 0).toFixed(2)}</div></div><div className="text-right"><div className="text-xl font-bold text-amber-400">{Number(task.acquisitionPriorityScore || 0).toFixed(2)}</div><Badge text={task.status}/></div></div><div className="text-xs text-slate-300 mt-3">{task.recommendedAction}</div>{task.evidenceType?.toLowerCase().includes("cctv") && bestCamera && <div className="mt-3 text-[11px] text-sky-300"><Camera size={12} className="inline mr-1"/>Best current target: {bestCamera.name} · {Math.round(bestCamera.distanceMeters)} m · preserve {dateTime(bestCamera.preservationWindowStart)} → {dateTime(bestCamera.preservationWindowEnd)}</div>}</div>)}</div>}</Panel>;
}

function RevisionPanel({ revisions, scoreHistory }) {
  const scores = new Map(scoreHistory.map((s) => [s.revision, s]));
  return <Panel title="Hypothesis Revision History"><div className="space-y-3">{[...revisions].reverse().map((r, idx) => { const revision = revisions.length - idx; const score = scores.get(revision); return <div key={revision} className="bg-slate-900/60 rounded-lg p-4"><div className="flex justify-between"><div className="font-semibold">Revision {revision}</div><div className="text-sm text-amber-400">{pct(pick(r, "machine_confidence", "machineConfidence"))}</div></div><div className="text-[11px] text-slate-500 mt-2">{pick(r, "classification") || "unclassified"} · {dateTime(pick(r, "start_time", "startTime"))}</div>{score && <div className="text-[11px] text-sky-300 mt-2">Canonical score {Math.round(score.score * 100)} · Tier {score.tier}</div>}</div>; })}</div></Panel>;
}

function LedgerPanel({ entries, integrity }) {
  return <div className="grid lg:grid-cols-3 gap-6"><Panel title="Ledger Integrity"><div className={`flex items-center gap-2 ${integrity?.valid ? "text-emerald-400" : "text-rose-400"}`}>{integrity?.valid ? <ShieldCheck size={18}/> : <AlertTriangle size={18}/>}<strong>{integrity?.valid ? "VALID HASH CHAIN" : "NOT VERIFIED"}</strong></div>{integrity?.error && <div className="text-xs text-rose-300 mt-3">{integrity.error}</div>}</Panel><Panel title="Decision Ledger" className="lg:col-span-2"><div className="space-y-2">{[...entries].reverse().map((e) => <div key={e.id} className="grid grid-cols-[70px_150px_1fr] gap-3 p-3 bg-slate-900/60 rounded text-[11px]"><div className="font-mono text-slate-600">#{e.sequenceNo}</div><div className="text-sky-400">{e.entryType}</div><div><div>{e.payload?.action || "ledger entry"}</div><div className="text-[9px] text-slate-600 mt-1">{e.producedBy} · {dateTime(e.createdAt)}</div></div></div>)}</div></Panel></div>;
}

function IntegrationBoundary() {
  return <Panel title="Independent Party & Compliance Boundary"><div className="grid md:grid-cols-2 gap-5"><div className="p-4 bg-slate-900/60 rounded-lg"><div className="text-sm font-semibold">Party Resolution</div><div className="text-[11px] text-slate-500 mt-2">The persistent camera layer does not identify a driver, owner, carrier, or claimant. Party resolution remains a separate evidence-backed workflow.</div></div><div className="p-4 bg-rose-950/20 border border-rose-900/50 rounded-lg"><div className="text-sm font-semibold text-rose-300">Contact Eligibility</div><div className="text-[11px] text-slate-500 mt-2">NOT_EVALUATED. Camera proximity, COS, correlation confidence, and attribution confidence do not authorize outreach.</div></div></div></Panel>;
}

function Panel({ title, children, className = "" }) { return <div className={`bg-[#0f1f38] border border-slate-800 rounded-xl p-5 ${className}`}><h2 className="text-sm font-semibold mb-4">{title}</h2>{children}</div>; }
function Section({ title, children }) { return <div className="mt-5"><div className="text-[10px] uppercase tracking-wide font-bold text-slate-500 mb-2">{title}</div><div className="text-sm leading-relaxed text-slate-300">{children}</div></div>; }
function BulletList({ items, danger = false }) { return <ul className={`list-disc pl-5 space-y-1 text-xs ${danger ? "text-rose-300" : "text-slate-300"}`}>{items.map((x, i) => <li key={`${i}-${x}`}>{String(x)}</li>)}</ul>; }
function Badge({ text, danger = false }) { return <span className={`inline-block px-2 py-0.5 rounded text-[10px] ${danger ? "bg-rose-950 text-rose-300" : "bg-slate-800 text-slate-400"}`}>{text}</span>; }
function Meta({ icon: Icon, label, value }) { return <div><div className="text-[9px] uppercase text-slate-600 flex items-center gap-1"><Icon size={11}/>{label}</div><div className="text-[11px] text-slate-300 mt-1">{value}</div></div>; }
function MetricCard({ label, value, help, color }) { return <div className="bg-[#0f1f38] border border-slate-800 rounded-xl p-4"><div className={`text-[10px] uppercase font-bold ${color}`}>{label}</div><div className="text-2xl font-bold mt-2">{value}</div><div className="text-[10px] text-slate-500 mt-1 leading-relaxed">{help}</div></div>; }
function DecisionRow({ label, value, danger = false }) { return <div className="flex justify-between gap-4 py-3 border-b border-slate-800 text-xs"><span className="text-slate-500">{label}</span><span className={danger ? "text-rose-300 font-semibold" : "text-slate-200"}>{String(value)}</span></div>; }
function Mini({ label, value }) { return <div className="bg-slate-950/60 rounded p-2"><div className="text-[9px] uppercase text-slate-600">{label}</div><div className="text-[10px] mt-1 text-slate-300">{value}</div></div>; }
function Muted({ children }) { return <div className="text-xs text-slate-500">{children}</div>; }
function Warning({ children }) { return <div className="mt-4 flex items-center gap-2 text-xs text-amber-300 bg-amber-950/20 border border-amber-800/40 rounded-lg p-3"><AlertTriangle size={14}/>{children}</div>; }
function LoadingState() { return <div className="p-10 text-center text-sm text-slate-500">Loading persisted case intelligence…</div>; }
function EmptyState({ title, text }) { return <div className="p-8 text-center bg-slate-900/50 border border-slate-800 rounded-xl"><MapPin size={26} className="mx-auto text-slate-600 mb-3"/><div className="font-semibold text-slate-300">{title}</div><div className="text-xs text-slate-500 mt-2">{text}</div></div>; }
