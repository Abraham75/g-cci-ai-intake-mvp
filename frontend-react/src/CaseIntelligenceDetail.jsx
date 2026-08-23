import React, { useEffect, useMemo, useState } from "react";
import {
  AlertTriangle,
  ArrowLeft,
  CheckCircle2,
  Clock3,
  Database,
  FileSearch,
  GitBranch,
  History,
  Info,
  MapPin,
  RefreshCw,
  Scale,
  ShieldAlert,
  ShieldCheck,
  Target,
} from "lucide-react";
import { gcciApi } from "./api.js";

const TABS = [
  ["overview", "Overview"],
  ["acquisition", "Evidence Acquisition"],
  ["revisions", "Revision History"],
  ["ledger", "Provenance / Ledger"],
  ["future", "Cameras · Parties · Compliance"],
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
    ledger: [],
    ledgerIntegrity: null,
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const load = async () => {
    if (!hypothesisId) return;
    setLoading(true);
    setError("");
    try {
      const [hypothesis, revisions, currentScore, scoreHistory, tasks, ledger, ledgerIntegrity] =
        await Promise.all([
          gcciApi.hypothesis(hypothesisId),
          gcciApi.hypothesisRevisions(hypothesisId),
          gcciApi.currentScore(hypothesisId),
          gcciApi.scoreHistory(hypothesisId),
          gcciApi.acquisitionTasks(hypothesisId),
          gcciApi.subjectLedger(hypothesisId),
          gcciApi.persistentLedgerIntegrity(),
        ]);
      setState({ hypothesis, revisions, currentScore, scoreHistory, tasks, ledger, ledgerIntegrity });
    } catch (e) {
      setError(e instanceof Error ? e.message : "Unknown case-intelligence error");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, [hypothesisId]);

  const vm = useMemo(() => buildViewModel(state, hypothesisId), [state, hypothesisId]);

  if (!hypothesisId) {
    return (
      <EmptyState
        title="No IncidentHypothesis selected"
        text="Open a correlated incident from the opportunity pipeline, or configure VITE_GCCI_DEMO_HYPOTHESIS_ID for a development default."
      />
    );
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
            <div className="text-[11px] text-slate-500 mt-1">
              {hypothesisId} · Revision {vm.revision} · {vm.location}
            </div>
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
          {tab === "acquisition" && <AcquisitionPanel tasks={state.tasks} />}
          {tab === "revisions" && <RevisionPanel revisions={state.revisions} scoreHistory={state.scoreHistory} />}
          {tab === "ledger" && <LedgerPanel entries={state.ledger} integrity={state.ledgerIntegrity} />}
          {tab === "future" && <IntegrationPanel />}
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
    roadway,
    direction,
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
    scoreConfidence: confidence,
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
          <div>
            <div className="text-[10px] uppercase text-slate-500">Case Opportunity Score</div>
            <div className="text-4xl font-bold text-amber-400">{vm.scoreAvailable ? Math.round(vm.score * 100) : "—"}</div>
          </div>
          <span className={`px-3 py-2 rounded text-xs font-bold ${TIER_STYLE[vm.tier] || "bg-slate-800 text-slate-400"}`}>TIER {vm.tier}</span>
        </div>
      </div>
      {vm.staleScore && (
        <div className="mt-4 flex items-center gap-2 text-xs text-amber-300 bg-amber-950/20 border border-amber-800/40 rounded-lg p-3">
          <AlertTriangle size={14} /> Hypothesis Revision {vm.revision} is newer than the latest completed score (Revision {vm.latestScoredRevision}). The UI is intentionally exposing that staleness.
        </div>
      )}
      {vm.pendingScoreJob && (
        <div className="mt-3 text-[11px] text-slate-500">Score job Revision {vm.pendingScoreJob.revision}: {vm.pendingScoreJob.status} · attempts {vm.pendingScoreJob.attempts}</div>
      )}
    </div>
  );
}

function ConfidenceStrip({ vm }) {
  const items = [
    ["Event Correlation", vm.eventCorrelation, "Do the source records describe the same event sequence?", "text-sky-400"],
    ["Causal Relationship", vm.causalRelationship, "Did one event materially cause or contribute to another?", "text-emerald-400"],
    ["Party Attribution", vm.partyAttribution, "Can responsibility be tied to a specific vehicle, person, carrier, or organization?", "text-rose-400"],
  ];
  return (
    <div className="grid md:grid-cols-4 gap-4">
      {items.map(([label, value, help, color]) => (
        <div key={label} className="bg-[#0f1f38] border border-slate-800 rounded-xl p-4">
          <div className={`text-[10px] uppercase font-bold ${color}`}>{label}</div>
          <div className="text-3xl font-bold mt-2">{pct(value)}</div>
          <div className="text-[10px] text-slate-500 mt-1 leading-relaxed">{help}</div>
        </div>
      ))}
      <div className="bg-[#0f1f38] border border-rose-900/50 rounded-xl p-4">
        <div className="text-[10px] uppercase font-bold text-rose-400">Contact Eligibility</div>
        <div className="text-xl font-bold text-rose-300 mt-3">{vm.contactEligibility}</div>
        <div className="text-[10px] text-slate-500 mt-2">Not inferred from COS, correlation, causation, or attribution. Independent compliance review is required.</div>
      </div>
    </div>
  );
}

function Overview({ vm }) {
  return (
    <div className="grid lg:grid-cols-3 gap-6">
      <Panel title="Attorney Executive Assessment" className="lg:col-span-2">
        <Section title="Current machine hypothesis">
          G-CCI currently classifies this record cluster as <strong>{vm.classification.replaceAll("_", " ")}</strong> with event-connection confidence of <strong>{pct(vm.eventCorrelation)}</strong>. This is an analytical hypothesis, not a party-liability finding.
        </Section>
        <Section title="Why the system connected these records">
          {vm.rationale.length ? <BulletList items={vm.rationale} /> : <Muted>No rationale was persisted on this revision.</Muted>}
        </Section>
        <Section title="Material contradictions">
          {vm.contradictions.length ? <BulletList items={vm.contradictions.map(String)} danger /> : <div className="flex items-center gap-2 text-emerald-400 text-xs"><CheckCircle2 size={14} />No contradiction is persisted on the current hypothesis revision.</div>}
        </Section>
        <Section title="Canonical score reasoning">
          {vm.scoreReasons.length ? <BulletList items={vm.scoreReasons} /> : <Muted>No canonical score reasons are available yet.</Muted>}
        </Section>
      </Panel>

      <Panel title="Current Decision State">
        <DecisionRow label="Hypothesis Revision" value={String(vm.revision)} />
        <DecisionRow label="Supporting Records" value={String(vm.memberIds.length)} />
        <DecisionRow label="Latest Scored Revision" value={vm.latestScoredRevision ?? "—"} />
        <DecisionRow label="COS / Tier" value={vm.scoreAvailable ? `${Math.round(vm.score * 100)} / ${vm.tier}` : "Pending"} />
        <DecisionRow label="Contact Eligibility" value="NOT_EVALUATED" danger />
        <div className="mt-5 p-3 rounded-lg bg-slate-900/60 text-[11px] text-slate-500 leading-relaxed">
          <Scale size={14} className="text-amber-400 mb-2" />
          Correlation, causation, party attribution, case economics, and permission to contact are deliberately separate decision dimensions.
        </div>
      </Panel>
    </div>
  );
}

function AcquisitionPanel({ tasks }) {
  const sorted = [...tasks].sort((a, b) => (b.acquisitionPriorityScore || 0) - (a.acquisitionPriorityScore || 0));
  return (
    <Panel title="Evidence Acquisition Queue">
      <p className="text-[11px] text-slate-500 mb-4">Prioritized from persisted evidence gaps and the completed canonical score. Older-revision work may remain visible as SUPERSEDED for auditability.</p>
      {!sorted.length ? <Muted>No acquisition tasks have been generated for this hypothesis.</Muted> : (
        <div className="overflow-x-auto">
          <table className="w-full text-xs">
            <thead className="text-[10px] uppercase text-slate-500 bg-slate-900/60"><tr><th className="text-left p-3">Evidence</th><th className="text-left p-3">EIG</th><th className="text-left p-3">Priority</th><th className="text-left p-3">Revision</th><th className="text-left p-3">Action</th><th className="text-left p-3">Status</th></tr></thead>
            <tbody>{sorted.map((task) => <tr key={task.id} className="border-t border-slate-800"><td className="p-3 font-medium text-slate-200">{task.evidenceType}</td><td className="p-3">{Number(task.expectedInformationGain || 0).toFixed(2)}</td><td className="p-3 text-amber-400 font-bold">{Number(task.acquisitionPriorityScore || 0).toFixed(2)}</td><td className="p-3">{task.revision}</td><td className="p-3 text-slate-400 max-w-md">{task.recommendedAction}</td><td className="p-3"><Badge text={task.status} danger={task.status === "SUPERSEDED"} /></td></tr>)}</tbody>
          </table>
        </div>
      )}
    </Panel>
  );
}

function RevisionPanel({ revisions, scoreHistory }) {
  const scores = new Map(scoreHistory.map((row) => [row.revision, row]));
  return (
    <Panel title="Immutable Hypothesis Revision History">
      <div className="space-y-3">
        {[...revisions].reverse().map((r, idx) => {
          const revision = pick(r, "revision") ?? revisions.length - idx;
          const score = scores.get(revision);
          return <div key={`${revision}-${idx}`} className="bg-slate-900/60 border border-slate-800 rounded-lg p-4"><div className="flex justify-between gap-4"><div><div className="font-semibold">Revision {revision}</div><div className="text-[11px] text-slate-500 mt-1">{pick(r, "classification") || "unclassified"} · {pick(r, "model_version", "modelVersion") || "model unknown"}</div></div><div className="text-right"><div className="text-lg font-bold text-sky-400">{pct(pick(r, "machine_confidence", "machineConfidence"))}</div><div className="text-[10px] text-slate-500">correlation</div></div></div><div className="mt-3 flex flex-wrap gap-2"><Badge text={`${(pick(r, "member_event_ids", "memberEventIds") || []).length} records`} />{score && <Badge text={`COS ${Math.round(score.score * 100)} · Tier ${score.tier}`} />}</div></div>;
        })}
      </div>
    </Panel>
  );
}

function LedgerPanel({ entries, integrity }) {
  return (
    <div className="grid lg:grid-cols-3 gap-6">
      <Panel title="Ledger Integrity">
        <div className={`flex items-center gap-2 text-sm font-semibold ${integrity?.valid ? "text-emerald-400" : "text-amber-400"}`}>
          {integrity?.valid ? <ShieldCheck size={17} /> : <ShieldAlert size={17} />}
          {integrity ? (integrity.valid ? "Hash chain valid" : "Integrity issue") : "Not checked"}
        </div>
        {integrity?.error && <div className="text-xs text-rose-300 mt-3">{integrity.error}</div>}
      </Panel>
      <Panel title="Decision Provenance" className="lg:col-span-2">
        {!entries.length ? <Muted>No ledger entries returned for this hypothesis.</Muted> : <div className="space-y-2">{entries.map((entry) => <div key={entry.id} className="grid md:grid-cols-[70px_160px_1fr] gap-3 bg-slate-900/50 rounded p-3 text-xs"><div className="font-mono text-slate-600">#{entry.sequenceNo}</div><div className="text-sky-400">{entry.entryType}</div><div><div className="text-slate-300">{summarizeLedgerPayload(entry.payload)}</div><div className="text-[10px] text-slate-600 mt-1">{entry.producedBy} · {dateTime(entry.createdAt)}</div></div></div>)}</div>}
      </Panel>
    </div>
  );
}

function summarizeLedgerPayload(payload) {
  if (!payload) return "No payload";
  if (payload.action) return String(payload.action).replaceAll("-", " ");
  if (payload.revision) return `Revision ${payload.revision}`;
  if (payload.result?.tier) return `Score result · Tier ${payload.result.tier}`;
  const keys = Object.keys(payload).slice(0, 4);
  return keys.length ? `Recorded: ${keys.join(", ")}` : "Ledger event recorded";
}

function IntegrationPanel() {
  const rows = [
    ["Persistent camera inventory", "NEXT", "Will support nearest-camera discovery, roadway/direction matching, preservation windows, and camera availability."],
    ["Contradiction detail endpoint", "PLANNED", "Current hypothesis exposes contradiction summaries; first-class evidence-cited resolution endpoint still needs a persistent API contract."],
    ["Party-resolution endpoint", "PLANNED", "UI will render UNKNOWN → CANDIDATE → CORROBORATED → VERIFIED without exposing unverified identity data."],
    ["Compliance-state endpoint", "PLANNED", "Contact eligibility must come from the independent compliance gateway; the UI intentionally does not infer it."],
  ];
  return <Panel title="Case Detail Integration Boundary"><div className="space-y-3">{rows.map(([name, status, text]) => <div key={name} className="bg-slate-900/60 rounded-lg p-4 flex gap-4"><Info size={15} className="text-sky-400 shrink-0 mt-0.5"/><div><div className="flex gap-2 items-center"><span className="font-medium text-sm">{name}</span><Badge text={status}/></div><div className="text-[11px] text-slate-500 mt-1 leading-relaxed">{text}</div></div></div>)}</div></Panel>;
}

function Panel({ title, className = "", children }) { return <div className={`bg-[#0f1f38] border border-slate-800 rounded-xl p-5 ${className}`}><h2 className="text-sm font-semibold text-slate-200 mb-4">{title}</h2>{children}</div>; }
function Section({ title, children }) { return <div className="mt-5"><div className="text-[10px] uppercase tracking-wide text-slate-500 font-bold mb-2">{title}</div><div className="text-sm text-slate-300 leading-relaxed">{children}</div></div>; }
function BulletList({ items, danger = false }) { return <ul className={`list-disc pl-5 space-y-1 text-xs ${danger ? "text-rose-300" : "text-slate-300"}`}>{items.map((item, i) => <li key={`${i}-${item}`}>{item}</li>)}</ul>; }
function Muted({ children }) { return <div className="text-xs text-slate-500">{children}</div>; }
function Badge({ text, danger = false }) { return <span className={`inline-flex px-2 py-1 rounded text-[10px] font-semibold ${danger ? "bg-rose-950 text-rose-300" : "bg-slate-800 text-slate-300"}`}>{text}</span>; }
function Meta({ icon: Icon, label, value }) { return <div className="flex gap-2"><Icon size={14} className="text-slate-500 shrink-0"/><div><div className="text-[9px] uppercase text-slate-600">{label}</div><div className="text-slate-400 mt-0.5">{value}</div></div></div>; }
function DecisionRow({ label, value, danger = false }) { return <div className="flex justify-between gap-3 py-3 border-b border-slate-800 text-xs"><span className="text-slate-500">{label}</span><span className={danger ? "text-rose-300 font-semibold" : "text-slate-200 font-semibold"}>{value}</span></div>; }
function LoadingState() { return <div className="bg-[#0f1f38] border border-slate-800 rounded-xl p-10 flex items-center justify-center gap-2 text-slate-500"><RefreshCw size={16} className="animate-spin"/>Loading case intelligence…</div>; }
function EmptyState({ title, text }) { return <div className="bg-[#0f1f38] border border-slate-800 rounded-xl p-10 text-center"><Database size={30} className="mx-auto text-slate-600 mb-3"/><div className="font-semibold text-slate-300">{title}</div><div className="text-xs text-slate-500 mt-2 max-w-lg mx-auto">{text}</div></div>; }
