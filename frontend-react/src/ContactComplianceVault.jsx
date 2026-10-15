import React, { useEffect, useMemo, useState } from "react";
import { Eye, EyeOff, LockKeyhole, RefreshCw, ShieldCheck, UserCheck } from "lucide-react";
import { gcciApi } from "./api.js";

const EMPTY_REVIEW = {
  legal_access_basis: "NotEstablished",
  solicitation_review_status: "NotReviewed",
  suppression_checked: false,
  solicitation_hold_days: "",
  note: "",
};

const EMPTY_CONTACT = {
  contact_type: "PHONE",
  value: "",
  source_type: "OFFICIAL_CRASH_REPORT",
  source_reference: "",
  lawful_access_basis: "NotEstablished",
  verification_confidence: "0.90",
  verified: false,
};

export default function ContactComplianceVault({ hypothesisId }) {
  const [gate, setGate] = useState(null);
  const [contacts, setContacts] = useState([]);
  const [prospects, setProspects] = useState([]);
  const [review, setReview] = useState(EMPTY_REVIEW);
  const [contact, setContact] = useState(EMPTY_CONTACT);
  const [revealReason, setRevealReason] = useState("");
  const [revealed, setRevealed] = useState({});
  const [status, setStatus] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const verifiedProspects = useMemo(
    () => prospects.filter((p) => p.partyRole === "INJURED_PARTY" && p.stage === "VERIFIED"),
    [prospects],
  );

  const load = async () => {
    if (!hypothesisId) return;
    setLoading(true);
    setError("");
    try {
      const [nextGate, nextContacts, nextProspects] = await Promise.all([
        gcciApi.complianceGate(hypothesisId),
        gcciApi.contacts(hypothesisId),
        gcciApi.prospects(hypothesisId),
      ]);
      setGate(nextGate);
      setContacts(nextContacts);
      setProspects(nextProspects);
      setReview({
        legal_access_basis: nextGate.legalAccessBasis || "NotEstablished",
        solicitation_review_status: nextGate.solicitationReviewStatus || "NotReviewed",
        suppression_checked: Boolean(nextGate.suppressionChecked),
        solicitation_hold_days: nextGate.solicitationHoldDays ?? "",
        note: "",
      });
    } catch (e) {
      setError(e instanceof Error ? e.message : "Contact/compliance load failed");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    setRevealed({});
    setRevealReason("");
    load();
  }, [hypothesisId]);

  const saveReview = async (event) => {
    event.preventDefault();
    setError("");
    setStatus("");
    try {
      await gcciApi.reviewCompliance(hypothesisId, {
        ...review,
        solicitation_hold_days:
          review.solicitation_hold_days === "" ? null : Number(review.solicitation_hold_days),
      });
      setStatus("Compliance review saved to the durable audit trail.");
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Compliance review failed");
    }
  };

  const addContact = async (event) => {
    event.preventDefault();
    setError("");
    setStatus("");
    const prospect = verifiedProspects[0];
    if (!prospect) {
      setError("A VERIFIED injured-party prospect is required before contact data can be stored.");
      return;
    }
    try {
      await gcciApi.addContact(hypothesisId, {
        prospect_id: prospect.id,
        contact_type: contact.contact_type,
        value: contact.value,
        source_type: contact.source_type,
        source_reference: contact.source_reference,
        lawful_access_basis: contact.lawful_access_basis,
        verification_confidence: Number(contact.verification_confidence),
        verified: Boolean(contact.verified),
      });
      setContact(EMPTY_CONTACT);
      setStatus("Contact encrypted and stored. Only the masked representation is displayed by default.");
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Contact storage failed");
    }
  };

  const reveal = async (contactId) => {
    setError("");
    setStatus("");
    if (revealReason.trim().length < 8) {
      setError("Enter an audit reason of at least 8 characters before revealing a contact value.");
      return;
    }
    try {
      const result = await gcciApi.revealContact(contactId, revealReason.trim());
      setRevealed((current) => ({ ...current, [contactId]: result.value }));
      setRevealReason("");
      setStatus("Contact reveal was authorized and written to the access audit trail.");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Contact reveal blocked");
    }
  };

  const activate = async () => {
    setError("");
    setStatus("");
    try {
      const result = await gcciApi.activateOutreach(hypothesisId);
      setStatus(result.status || "Outreach activation approved.");
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Outreach activation blocked");
    }
  };

  const eligible = gate?.contactEligibilityStatus === "Eligible";
  const verifiedContact = contacts.some((c) => c.verified && c.status === "ACTIVE");
  const activationReady = eligible && verifiedProspects.length > 0 && verifiedContact;

  return (
    <section className="mt-8 border-t border-slate-800 pt-8 space-y-5">
      <div className="flex items-start justify-between gap-4">
        <div>
          <div className="text-[10px] uppercase tracking-[0.18em] text-emerald-400 font-bold">Secure Contact & Compliance</div>
          <h2 className="text-xl font-bold text-slate-100 mt-1">Contact Resolution Vault</h2>
          <p className="text-[11px] text-slate-500 mt-1 max-w-3xl">
            Contact values are encrypted before database storage. Masked values are the default view; reveal and outreach activation require independent compliance clearance and are audited.
          </p>
        </div>
        <button onClick={load} disabled={loading} className="flex items-center gap-2 px-3 py-2 bg-slate-800 rounded-lg text-xs hover:bg-slate-700 disabled:opacity-50">
          <RefreshCw size={13} className={loading ? "animate-spin" : ""} /> Refresh vault
        </button>
      </div>

      {error && <div className="rounded-xl border border-rose-800 bg-rose-950/30 p-4 text-sm text-rose-300">{error}</div>}
      {status && <div className="rounded-xl border border-emerald-800 bg-emerald-950/20 p-4 text-sm text-emerald-300">{status}</div>}

      <div className="grid lg:grid-cols-4 gap-3">
        <StateCard label="Verified prospect" value={verifiedProspects.length ? "YES" : "NO"} good={verifiedProspects.length > 0} />
        <StateCard label="Verified contact" value={verifiedContact ? "YES" : "NO"} good={verifiedContact} />
        <StateCard label="Compliance" value={gate?.contactEligibilityStatus || "NotEvaluated"} good={eligible} />
        <StateCard label="Activation ready" value={activationReady ? "YES" : "NO"} good={activationReady} />
      </div>

      <div className="grid xl:grid-cols-2 gap-5">
        <Panel title="Compliance Review" icon={ShieldCheck}>
          <form onSubmit={saveReview} className="space-y-3">
            <Field label="Legal access basis">
              <select value={review.legal_access_basis} onChange={(e) => setReview({ ...review, legal_access_basis: e.target.value })} className={inputClass}>
                <option>NotEstablished</option><option>PublicRecord</option><option>OpenRecordsRequest</option><option>ClientProvided</option><option>OtherLawfulBasis</option>
              </select>
            </Field>
            <Field label="Solicitation review status">
              <select value={review.solicitation_review_status} onChange={(e) => setReview({ ...review, solicitation_review_status: e.target.value })} className={inputClass}>
                <option>NotReviewed</option><option>WithinHoldPeriod</option><option>ClearedByCounsel</option><option>RejectedByCounsel</option>
              </select>
            </Field>
            <Field label="Hold days (policy metadata)"><input type="number" min="0" max="3650" value={review.solicitation_hold_days} onChange={(e) => setReview({ ...review, solicitation_hold_days: e.target.value })} className={inputClass} /></Field>
            <label className="flex items-center gap-2 text-xs text-slate-300"><input type="checkbox" checked={review.suppression_checked} onChange={(e) => setReview({ ...review, suppression_checked: e.target.checked })} />Suppression / do-not-contact check completed</label>
            <Field label="Counsel/compliance note"><textarea value={review.note} onChange={(e) => setReview({ ...review, note: e.target.value })} className={`${inputClass} min-h-20`} /></Field>
            <button className={primaryButton}>Save compliance review</button>
          </form>
        </Panel>

        <Panel title="Add Verified Contact Source" icon={LockKeyhole}>
          {!verifiedProspects.length ? (
            <Muted>Contact storage is disabled until an injured-party prospect reaches VERIFIED through evidence-backed resolution.</Muted>
          ) : (
            <form onSubmit={addContact} className="space-y-3">
              <div className="text-[11px] text-slate-500">Prospect: {verifiedProspects[0].displayLabel || verifiedProspects[0].id}</div>
              <div className="grid md:grid-cols-2 gap-3">
                <Field label="Contact type"><select value={contact.contact_type} onChange={(e) => setContact({ ...contact, contact_type: e.target.value })} className={inputClass}><option>PHONE</option><option>EMAIL</option><option>ADDRESS</option><option>OTHER</option></select></Field>
                <Field label="Contact value"><input autoComplete="off" value={contact.value} onChange={(e) => setContact({ ...contact, value: e.target.value })} className={inputClass} required /></Field>
                <Field label="Source type"><input value={contact.source_type} onChange={(e) => setContact({ ...contact, source_type: e.target.value })} className={inputClass} required /></Field>
                <Field label="Source reference"><input value={contact.source_reference} onChange={(e) => setContact({ ...contact, source_reference: e.target.value })} className={inputClass} required /></Field>
                <Field label="Lawful access basis"><select value={contact.lawful_access_basis} onChange={(e) => setContact({ ...contact, lawful_access_basis: e.target.value })} className={inputClass}><option>NotEstablished</option><option>PublicRecord</option><option>OpenRecordsRequest</option><option>ClientProvided</option><option>OtherLawfulBasis</option></select></Field>
                <Field label="Verification confidence"><input type="number" min="0" max="1" step="0.01" value={contact.verification_confidence} onChange={(e) => setContact({ ...contact, verification_confidence: e.target.value })} className={inputClass} /></Field>
              </div>
              <label className="flex items-center gap-2 text-xs text-slate-300"><input type="checkbox" checked={contact.verified} onChange={(e) => setContact({ ...contact, verified: e.target.checked })} />Contact value independently verified</label>
              <button className={primaryButton}>Encrypt & store contact</button>
            </form>
          )}
        </Panel>
      </div>

      <Panel title="Masked Contact Records" icon={UserCheck}>
        {!contacts.length ? <Muted>No contact records are stored for this hypothesis.</Muted> : (
          <div className="space-y-3">
            <div className="flex gap-3 items-end">
              <Field label="Required reveal reason"><input value={revealReason} onChange={(e) => setRevealReason(e.target.value)} placeholder="Attorney review for approved outreach" className={inputClass} /></Field>
            </div>
            {contacts.map((item) => (
              <div key={item.id} className="grid lg:grid-cols-[1.2fr_1fr_1fr_auto] gap-3 items-center border border-slate-800 rounded-lg p-3 bg-slate-900/40 text-xs">
                <div><div className="text-slate-200 font-medium">{item.contactType}</div><div className="text-slate-400 mt-1">{revealed[item.id] || item.maskedValue}</div></div>
                <div><div className="text-[10px] uppercase text-slate-600">Source</div><div className="text-slate-400 mt-1">{item.sourceType} · {item.sourceReference}</div></div>
                <div><div className="text-[10px] uppercase text-slate-600">Verification</div><div className={item.verified ? "text-emerald-400 mt-1" : "text-amber-400 mt-1"}>{item.verified ? "VERIFIED" : "UNVERIFIED"} · {Math.round((item.verificationConfidence || 0) * 100)}%</div></div>
                <button type="button" onClick={() => revealed[item.id] ? setRevealed((current) => ({ ...current, [item.id]: undefined })) : reveal(item.id)} className="flex items-center gap-1.5 px-3 py-2 rounded bg-slate-800 hover:bg-slate-700">
                  {revealed[item.id] ? <EyeOff size={13} /> : <Eye size={13} />}{revealed[item.id] ? "Hide" : "Reveal"}
                </button>
              </div>
            ))}
          </div>
        )}
      </Panel>

      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 rounded-xl border border-slate-800 bg-[#0f1f38] p-5">
        <div>
          <div className="text-sm font-semibold">Outreach Activation</div>
          <div className="text-[11px] text-slate-500 mt-1">Requires VERIFIED injured party + verified active contact + durable compliance status Eligible. The server re-checks all gates at activation time.</div>
        </div>
        <button onClick={activate} className={`${activationReady ? primaryButton : "px-4 py-2 rounded bg-slate-800 text-slate-500"}`}>
          Activate for attorney outreach
        </button>
      </div>
    </section>
  );
}

const inputClass = "w-full bg-slate-950 border border-slate-700 rounded-lg px-3 py-2 text-xs text-slate-200 focus:outline-none focus:border-amber-500";
const primaryButton = "px-4 py-2 rounded-lg bg-amber-500 text-slate-950 text-xs font-semibold hover:bg-amber-400";

function Panel({ title, icon: Icon, children }) {
  return <div className="bg-[#0f1f38] border border-slate-800 rounded-xl p-5"><div className="flex items-center gap-2 text-sm font-semibold mb-4">{Icon && <Icon size={14} className="text-amber-400" />}{title}</div>{children}</div>;
}

function Field({ label, children }) {
  return <label className="block flex-1"><span className="block text-[10px] uppercase tracking-wide text-slate-500 mb-1">{label}</span>{children}</label>;
}

function StateCard({ label, value, good }) {
  return <div className="bg-[#0f1f38] border border-slate-800 rounded-xl p-4"><div className="text-[10px] uppercase text-slate-500">{label}</div><div className={`text-lg font-bold mt-2 ${good ? "text-emerald-400" : "text-rose-400"}`}>{value}</div></div>;
}

function Muted({ children }) {
  return <div className="text-xs text-slate-500 leading-relaxed">{children}</div>;
}
