import React, { useEffect, useMemo, useState } from "react";
import {
  AlertTriangle,
  CheckCircle2,
  FileSearch,
  RefreshCw,
  Scale,
  ShieldAlert,
  Target,
  UserSearch,
} from "lucide-react";
import { gcciApi } from "./api.js";

const PIPELINE = [
  ["S0_SIGNAL", "Signal", "Potential truck-event signal"],
  ["S1_OPPORTUNITY", "Opportunity", "Worth further investigation"],
  ["S2_QUALIFIED_CASE", "Qualified Case", "Case-value and minimum evidence gates passed"],
  ["S3_RESOLVED_PROSPECT", "Resolved Prospect", "Injured party verified; compliance still separate"],
];

const STAGE_INDEX = Object.fromEntries(PIPELINE.map(([id], index) => [id, index]));

function pct(value) {
  return typeof value === "number" ? `${Math.round(value * 100)}%` : "—";
}

export default function LeadQualificationWorkspace({ hypothesisId }) {
  const [data, setData] = useState({ qualification: null, tasks: [], prospects: [], gate: null });
  const [loading, setLoading] = useState(false);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState("");

  const load = async () => {
    if (!hypothesisId) return;
    setLoading(true);
    setError("");
    try {
      const [qualification, tasks, prospects, gate] = await Promise.all([
        gcciApi.leadQualification(hypothesisId).catch((e) => ({ status: "UNAVAILABLE", error: e.message })),
        gcciApi.resolutionTasks(hypothesisId, true).catch(() => []),
        gcciApi.prospects(hypothesisId).catch(() => []),
        gcciApi.complianceGate(hypothesisId).catch(() => null),
      ]);
      setData({ qualification, tasks, prospects, gate });
    } catch (e) {
      setError(e instanceof Error ? e.message : "Lead qualification load failed");
    } finally {
      setLoading(false);
    }
  };

  const refresh = async () => {
    if (!hypothesisId) return;
    setRefreshing(true);
    setError("");
    try {
      await gcciApi.refreshLeadQualification(hypothesisId);
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Lead qualification refresh failed");
    } finally {
      setRefreshing(false);
    }
  };

  useEffect(() => {
    load();
  }, [hypothesisId]);

  const q = data.qualification || {};
  const currentIndex = STAGE_INDEX[q.stage] ?? -1;
  const verifiedProspect = useMemo(
    () => data.prospects.find((p) => p.partyRole === "INJURED_PARTY" && p.stage === "VERIFIED") || null,
    [data.prospects],
  );
  const contactEligible = data.gate?.contactEligibilityStatus === "Eligible";
  const outreachReady = q.stage === "S3_RESOLVED_PROSPECT" && contactEligible;

  return (
    <section className="mt-8 border-t border-slate-800 pt-8 space-y-6">
      <div className="flex items-start justify-between gap-4">
        <div>
          <div className="text-[10px] uppercase tracking-[0.18em] text-amber-400 font-bold">Lead Qualification & Resolution Engine</div>
          <h2 className="text-xl font-bold text-slate-100 mt-1">Attorney Lead Readiness</h2>
          <p className="text-[11px] text-slate-500 mt-1 max-w-3xl">
            Converts a case opportunity into an evidence-backed prospect. It may rank the next source to investigate; it does not guess a person’s identity and it cannot authorize outreach.
          </p>
        </div>
        <button onClick={refresh} disabled={refreshing || loading} className="flex items-center gap-2 px-3 py-2 bg-slate-800 rounded-lg text-xs hover:bg-slate-700 disabled:opacity-50">
          <RefreshCw size={13} className={refreshing ? "animate-spin" : ""} /> Re-evaluate lead
        </button>
      </div>

      {error && <div className="border border-rose-800 bg-rose-950/30 text-rose-300 rounded-xl p-4 text-sm">{error}</div>}

      <div className="grid lg:grid-cols-4 gap-3">
        {PIPELINE.map(([id, label, help], index) => {
          const reached = currentIndex >= index;
          const active = q.stage === id;
          return (
            <div key={id} className={`rounded-xl border p-4 ${active ? "border-amber-500/70 bg-amber-500/10" : reached ? "border-emerald-800 bg-emerald-950/20" : "border-slate-800 bg-[#0f1f38]"}`}>
              <div className="flex items-center justify-between gap-2">
                <div className="text-[10px] uppercase text-slate-500">{id}</div>
                {reached ? <CheckCircle2 size={14} className="text-emerald-400" /> : <div className="w-3 h-3 rounded-full border border-slate-700" />}
              </div>
              <div className="font-semibold mt-2">{label}</div>
              <div className="text-[10px] text-slate-500 mt-1 leading-relaxed">{help}</div>
            </div>
          );
        })}
      </div>

      <div className="grid xl:grid-cols-3 gap-5">
        <Panel title="Qualification Decision" icon={Scale}>
          {q.status === "PENDING_QUALIFICATION" ? (
            <Muted>Canonical scoring exists but lead qualification has not run yet. Use Re-evaluate Lead.</Muted>
          ) : q.status === "UNAVAILABLE" ? (
            <Muted>Qualification service is unavailable: {q.error}</Muted>
          ) : (
            <>
              <DecisionRow label="Lead stage" value={q.stage || "—"} />
              <DecisionRow label="Qualification score" value={pct(q.qualificationScore)} />
              <DecisionRow label="Case qualified" value={q.caseQualified ? "YES" : "NO"} good={q.caseQualified} />
              <DecisionRow label="Claimant resolution" value={q.claimantResolutionStage || "UNKNOWN"} />
              <DecisionRow label="Contact eligibility" value={data.gate?.contactEligibilityStatus || "NOT_EVALUATED"} danger={!contactEligible} good={contactEligible} />
              <DecisionRow label="Outreach ready" value={outreachReady ? "YES" : "NO"} danger={!outreachReady} good={outreachReady} />
            </>
          )}
        </Panel>

        <Panel title="Validated Case Dimensions" icon={Target}>
          <Dimension label="Case Opportunity" value={q.dimensions?.caseOpportunityScore} />
          <Dimension label="Injury" value={q.dimensions?.injury} />
          <Dimension label="Liability" value={q.dimensions?.liability} />
          <Dimension label="Collectability" value={q.dimensions?.collectability} />
          <Dimension label="Evidence" value={q.dimensions?.evidence} />
          <Dimension label="Defendant Resolution" value={q.dimensions?.defendantResolution} />
        </Panel>

        <Panel title="Prospect Resolution" icon={UserSearch}>
          <DecisionRow label="Injured party" value={verifiedProspect ? "VERIFIED" : q.claimantResolutionStage || "UNKNOWN"} good={Boolean(verifiedProspect)} />
          {verifiedProspect ? (
            <div className="mt-4 p-3 rounded-lg bg-emerald-950/20 border border-emerald-900/50 text-xs">
              <div className="font-semibold text-emerald-300">Evidence-backed prospect</div>
              <div className="text-slate-400 mt-2">Source: {verifiedProspect.sourceType}</div>
              <div className="text-slate-500 mt-1">Reference: {verifiedProspect.sourceReference}</div>
              <div className="text-slate-500 mt-1">Lawful access: {verifiedProspect.lawfulAccessBasis}</div>
            </div>
          ) : (
            <div className="mt-4 p-3 rounded-lg bg-slate-900/60 text-[11px] text-slate-500 leading-relaxed">
              No verified injured-party record exists yet. The engine ranks evidence sources below instead of manufacturing an identity from fuzzy correlation.
            </div>
          )}
        </Panel>
      </div>

      <div className="grid lg:grid-cols-2 gap-5">
        <Panel title="Why This Lead Is / Is Not Qualified" icon={FileSearch}>
          <Subhead>Supporting reasons</Subhead>
          {q.reasons?.length ? <BulletList items={q.reasons} /> : <Muted>No qualification reasons recorded.</Muted>}
          <Subhead>Blockers</Subhead>
          {q.blockers?.length ? <BulletList items={q.blockers} danger /> : <div className="flex items-center gap-2 text-emerald-400 text-xs"><CheckCircle2 size={13} />No qualification blocker recorded.</div>}
          <Subhead>Required next actions</Subhead>
          {q.requiredActions?.length ? <BulletList items={q.requiredActions} /> : <Muted>No required action recorded.</Muted>}
        </Panel>

        <Panel title="Independent Outreach Gate" icon={ShieldAlert}>
          <DecisionRow label="Legal access basis" value={data.gate?.legalAccessBasis || "NotEstablished"} />
          <DecisionRow label="Solicitation review" value={data.gate?.solicitationReviewStatus || "NotReviewed"} />
          <DecisionRow label="Suppression check" value={data.gate?.suppressionChecked ? "COMPLETE" : "INCOMPLETE"} good={data.gate?.suppressionChecked} danger={!data.gate?.suppressionChecked} />
          <DecisionRow label="Contact eligibility" value={data.gate?.contactEligibilityStatus || "NotEvaluated"} good={contactEligible} danger={!contactEligible} />
          <div className="mt-4 p-3 rounded-lg bg-rose-950/20 border border-rose-900/40 text-[11px] text-slate-400 leading-relaxed">
            A Tier A case, verified prospect, or available contact source does not authorize outreach. Counsel/compliance clearance remains an independent hard gate.
          </div>
        </Panel>
      </div>

      <Panel title="Best Sources to Resolve the Injured Party" icon={UserSearch}>
        {!data.tasks.length ? (
          verifiedProspect ? <Muted>Claimant resolution is VERIFIED; no open identity-resolution tasks remain.</Muted> : <Muted>No open resolution tasks are available.</Muted>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-xs">
              <thead className="text-[10px] uppercase text-slate-500 bg-slate-900/60">
                <tr>
                  <th className="text-left p-3">Priority</th>
                  <th className="text-left p-3">Source</th>
                  <th className="text-left p-3">Question</th>
                  <th className="text-left p-3">P(resolve)</th>
                  <th className="text-left p-3">Reliability</th>
                  <th className="text-left p-3">Recommended action</th>
                </tr>
              </thead>
              <tbody>
                {data.tasks.map((task, index) => (
                  <tr key={task.id} className="border-t border-slate-800 align-top">
                    <td className="p-3"><span className="text-amber-400 font-bold">#{index + 1}</span><div className="text-[10px] text-slate-500 mt-1">{pct(task.resolutionPriorityScore)}</div></td>
                    <td className="p-3 font-medium text-slate-200">{task.sourceType.replaceAll("_", " ")}</td>
                    <td className="p-3 text-slate-400 max-w-xs">{task.question}</td>
                    <td className="p-3">{pct(task.probabilityResolves)}</td>
                    <td className="p-3">{pct(task.sourceReliability)}</td>
                    <td className="p-3 text-slate-400 max-w-md">{task.recommendedAction}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Panel>

      <div className="flex items-start gap-2 rounded-xl border border-amber-900/40 bg-amber-950/10 p-4 text-[11px] text-slate-400 leading-relaxed">
        <AlertTriangle size={15} className="text-amber-400 shrink-0 mt-0.5" />
        Identity resolution requires source evidence and staged review: UNKNOWN → CANDIDATE → CORROBORATED → VERIFIED. The engine is allowed to recommend where to look next; it is not allowed to convert proximity, name similarity, social-media similarity, or case value into a verified person.
      </div>
    </section>
  );
}

function Panel({ title, icon: Icon, children }) {
  return <div className="bg-[#0f1f38] border border-slate-800 rounded-xl p-5"><div className="flex items-center gap-2 text-sm font-semibold mb-4">{Icon && <Icon size={14} className="text-amber-400" />}{title}</div>{children}</div>;
}

function DecisionRow({ label, value, good = false, danger = false }) {
  return <div className="flex items-center justify-between gap-4 py-2.5 border-b border-slate-800 last:border-0 text-xs"><span className="text-slate-500">{label}</span><span className={`font-medium text-right ${good ? "text-emerald-400" : danger ? "text-rose-400" : "text-slate-200"}`}>{String(value ?? "—")}</span></div>;
}

function Dimension({ label, value }) {
  const n = typeof value === "number" ? value : 0;
  return <div className="mb-3"><div className="flex justify-between text-[11px] mb-1"><span className="text-slate-500">{label}</span><span>{typeof value === "number" ? pct(value) : "—"}</span></div><div className="h-1.5 bg-slate-900 rounded overflow-hidden"><div className="h-full bg-amber-500" style={{ width: `${Math.round(n * 100)}%` }} /></div></div>;
}

function Subhead({ children }) {
  return <div className="text-[10px] uppercase tracking-wider text-slate-500 font-bold mt-4 mb-2 first:mt-0">{children}</div>;
}

function BulletList({ items, danger = false }) {
  return <ul className={`text-xs space-y-1.5 list-disc pl-5 ${danger ? "text-rose-300" : "text-slate-400"}`}>{items.map((item, i) => <li key={`${i}-${item}`}>{item}</li>)}</ul>;
}

function Muted({ children }) {
  return <div className="text-xs text-slate-500 leading-relaxed">{children}</div>;
}
