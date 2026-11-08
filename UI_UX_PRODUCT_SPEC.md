# G-CCI — UI/UX Product Design & Implementation Specification
Version 1.0 | 2026-11-08 | Status: Proposed design contract, not a claim of completed implementation

## 1. Product promise
G-CCI helps plaintiff-side trucking litigators and investigators decide **which incidents merit investigation, why, what evidence to obtain next, and what they are legally permitted to do**. It is an evidence-first attorney decision-support system, not a lead-selling dashboard, autonomous legal adviser, identity inference engine, or outreach automation.

**North-star user outcome:** An attorney can open the queue, identify the highest-priority credible opportunity, understand the strongest and weakest evidence, assign a lawful next action, and record a defensible disposition in under five minutes. This is a design hypothesis to test, not a measured claim.

## 2. Evidence and research basis
- W3C WCAG 2.2 (https://www.w3.org/TR/WCAG22/): target WCAG 2.2 AA, keyboard access, focus visibility, text contrast, target sizes, predictable interaction, errors and status messaging.
- Nielsen Norman Group, 8 Design Guidelines for Complex Applications (https://www.nngroup.com/articles/complex-application-design/): support expert nonlinear workflows, reduce clutter without reducing capability, preserve context while inspecting details.
- Nielsen Norman Group, Progressive Disclosure (https://www.nngroup.com/articles/progressive-disclosure/): primary tasks visible; specialized evidence and administrative diagnostics secondary.
- Existing repository implementation inspected 2026-11-08: `frontend-react/src/App.jsx`, `OpportunityRadar.jsx`, `CaseIntelligenceDetail.jsx`. Observed current three-item navigation and case-detail tabs. The present implementation has usability and robustness gaps; this specification describes a target, not a validated user-tested design.

## 3. User roles and permissions
| Role | Primary job | Primary screens | Write permissions |
|---|---|---|---|
| Attorney | Decide investigation value and record case outcome | Radar, Case Intelligence, Decision Review | Attorney dispositions, outcomes; no implied outreach permission |
| Investigator | Corroborate incidents and gather evidence | Radar, Case Intelligence, Evidence Tasks | Evidence notes/tasks subject to server authorization |
| Compliance reviewer | Review identity, source legality, jurisdiction and solicitation restrictions | Compliance Review | Independent clearance only |
| Auditor | Trace decisions and provenance | Audit view, validation reports | Read-only |
| Administrator/SRE | Monitor feeds, configuration, access, health | Platform Status | Restricted admin actions |

All UI controls must be capability-driven by the authenticated server role, not hidden merely with CSS. Unauthorized mutations must fail server-side. The backend must derive reviewer identity from authentication, not client-submitted names.

## 4. Information architecture — minimal first
Primary:
1. **Opportunity Radar** (default, attorney priority queue)
2. **Case Intelligence** (case dossier and investigation workflow)
3. **Platform Status** (only for authorized technical roles)

Within Case Intelligence:
- Overview (why this case; why it might be wrong)
- Evidence & Next Actions
- Sources, Contradictions & Timeline
- Location & Cameras
- Parties & Compliance (role gated)
- Decision History (audit / provenance)

Do not add top-level AI Agents, Chatbot, Decision Economics, Live Signals, or ontology screens unless pilot research demonstrates that they improve task completion. Advanced data can remain in contextual panels.

## 5. Essential interaction flow
```
Sign in -> Opportunity Radar -> Filter/sort -> Open opportunity
-> Inspect rationale + contradictory evidence -> Open cited source
-> Choose next evidence action OR record attorney disposition
-> Confirm irreversible/high-impact action -> Audit receipt
-> Return to queue with preserved filters/scroll/selection
```

Alternative flows: not enough evidence -> evidence task; false positive -> reason-coded rejection; conflicting sources -> contradiction resolution; no matching data -> explicit empty state; stale scoring -> block confident display; forbidden action -> permission explanation, no mutation.

## 6. Screen contracts

### A. Opportunity Radar
**Above the fold:** title, last successful data refresh, source freshness warning, prioritized list, filters, and an explicit distinction between scoring and attorney disposition.

Queue row fields:
- Roadway / incident location, occurrence time with timezone
- Tier and canonical COS (show as *model-derived ranking*, not probability of winning)
- Correlation confidence separately from COS
- Evidence sufficiency, unresolved contradictions, and source freshness
- One-line 'Why prioritized'
- Next best evidence action, deadline/preservation urgency when known
- Attorney review status and assignment
- CTA: 'Review case'

Filters: tier, reviewed/unreviewed, source freshness, contradiction severity, county/roadway, occurrence date, assigned reviewer. Default sort by validated prioritization; user may change. Save query state in URL; preserve on return. Paginate on server; do not interpret the first 50 as the total corpus.

**No false precision:** show N/A when metrics lack adequate labels; show denominator, date range, cohort and methodology in metric detail. Never call a COS of 0.82 an '82% chance of success'.

**Disposition UX:** select disposition and reason; optional note; preview before submit; server-authenticated reviewer; show timestamp and audit receipt; optimistic updates only with rollback on error. 'Needs more information' must not be counted as negative ground truth.

### B. Case Intelligence
Sticky case header: location/time, hypothesis revision, score revision, tier, current evidence status, assigned owner, next action. When score revision lags hypothesis revision, show **STALE SCORE** prominently and avoid unqualified ranking language.

**Why this case?** Summarize supporting facts, missing facts, contradicting facts, and uncertainty separately. Every material claim links to a source, source timestamp, access basis, and evidence type. Clearly label inferred vs observed vs attorney-confirmed.

**Evidence timeline:** chronological event and source observations, each with time provenance; preserve ambiguity when timestamps disagree.

**Contradiction workbench:** conflict pair, severity, implications, source links, assigned resolver, status. Resolving contradiction is a human-reviewed state transition with audit history.

**Evidence task:** task description, source, expected information gain, preservation deadline, lawful acquisition route, owner, status, completion evidence. No invented deadlines or certainty.

**Map/cameras:** optional spatial context, camera coverage and estimated relevance; never infer footage exists or proves causation. List fallback required for keyboard and screen reader access.

**Compliance:** contact eligibility and outreach authorization displayed independently of case score; default blocked or not evaluated. Never expose contact information without server permission and audit.

### C. Validation view (authorized research/admin)
Cohort selector, sample size, reviewed fraction, Precision@K, discovery recall, investigation yield, and time advantage with uncertainty notes. Separate historical benchmark performance from live pilot outcomes. Warn on missing labels, selection bias, cohort drift and sample size. Never compare scores across versions without a visible version label.

### D. Platform Status
Show operational health, last successful feed ingestion, scoring lag, migration status, service dependency failures, queue backlog and ledger integrity. A healthy HTTP endpoint alone does not mean the pipeline is healthy. Restrict sensitive operational details by role.

## 7. Visual design system
Direction: restrained forensic research workspace, high signal-to-noise, not cinematic surveillance UI.

Tokens (proposed, subject to contrast testing):
- Background #0B1220, surface #111D2E, raised surface #18263A
- Primary text #F3F6FA, secondary #B9C7D8
- Action blue #73B8FF; verified green #6DD3A5
- Warning amber #F2BE65; blocked red #FF818C
- Focus ring #9DD1FF; separators #31425B
- Font: system UI / Inter-like sans-serif; tabular numerals for metrics; minimum normal body 14–16 px on desktop.
- Spacing: 4 px base grid, 8/12/16/24/32 steps; minimum 44 px preferred primary action target.
- No color-only state coding; always pair color with text and optionally icon.
- One primary CTA per panel; no decorative KPI cards that do not change decisions.

Responsive: desktop 1440 and 1280, laptop 1024, tablet 768, mobile 390. On narrow screens, queue becomes stacked cards and detailed tables become labeled sections; no hidden critical evidence. Mobile is for triage, not forced full forensic analysis.

## 8. Content and terminology rules
Use: 'Case opportunity score', 'Correlated incident', 'Evidence suggests', 'Unverified', 'Needs attorney review', 'Contact not authorized', 'Source unavailable'.
Avoid: 'Guaranteed case', 'Victim identified', 'AI proved liability', 'Safe to contact', 'Winning probability' unless an independently validated and explicitly defined model supports the claim.

Keep these dimensions distinct:
```
Event correlation != causation != party attribution != case opportunity
!= claimant resolution != contact eligibility != outreach authorization
```

## 9. States and error handling
Every API-dependent component needs: loading, no results, no permission, stale data, partial data, offline/network error, retry, success and mutation conflict. Show last-known-good data with an explicit stale marker where safe. Never silently turn an API failure into zero cases. Long requests need progress messaging; repeated submissions must be disabled or idempotent. Error text must say what failed and whether data was saved.

## 10. Accessibility and trust acceptance
- Target WCAG 2.2 AA; verify with axe and manual keyboard/screen reader tests.
- All controls reachable by keyboard; visible focus; meaningful labels and landmarks.
- Data tables have semantic headers and sorting state.
- Status updates announced without stealing focus.
- Dialogs manage focus, escape, cancel, confirm and return focus.
- Respect reduced motion and 200% zoom/reflow.
- Contrast: normal text >= 4.5:1; large text >= 3:1; non-text UI >= 3:1 where applicable.
- No reliance on hover-only evidence or map-only information.
- Audit and identity fields are server authoritative.

## 11. Usability research plan
Recruit 5–8 practicing trucking plaintiff attorneys/investigators for formative testing, plus 2 compliance/audit users; these are recruitment targets, not statistical validation. Test representative tasks using sanitized historical cases:
1. Find top 3 cases worth reviewing.
2. Explain why the highest-ranked case may be a false positive.
3. Find and cite the source supporting an injury indicator.
4. Assign the highest-value next evidence action.
5. Reject a weak case with a defensible reason.
6. Identify whether outreach is authorized without confusing score and permission.
7. Recover from an API timeout or stale score.
8. Return to the same filtered queue.

Record task success, time-on-task, errors, unsupported claims, evidence-source retrieval, and post-task confidence. Set numeric launch thresholds only after baseline pilot results; never invent benchmark success.

## 12. Implementation backlog
**P0 — trust and function**
- Remove stale/undefined `DecisionEconomicsDashboard` reference in App.
- Remove `VITE_GCCI_REVIEWER` as a source of decision identity.
- Hide mutation controls when role lacks permission; backend must enforce.
- Separate Radar data and metrics fetching so metrics failure does not erase the case queue.
- Make feedback mutation pending/disabled and show success receipt.
- Explicit loading/empty/error/stale states, no misleading zero metrics.
- Correct pagination/total-count semantics; expose cohort sizes for KPIs.
- Make Case Intelligence resilient to partial subservice failure; do not blank all evidence because a camera or ledger request fails.

**P1 — investigative usefulness**
- Source-linked rationale, contradiction panel, evidence task assignment, preserved queue context.
- Date/timezone clarity and freshness indicators.
- Filter/search and accessible keyboard-first case navigation.
- Case revision/score revision discrepancy warning.

**P2 — validation and efficiency**
- Authorized validation view with cohort and methodology metadata.
- Evidence acquisition task outcomes and usability telemetry (no private contact details in analytics).
- Controlled comparisons of prioritization and evidence layouts.

## 13. Engineering handoff / component map
Proposed React components:
```
AppShell
  AuthBoundary
  PrimaryNavigation
  OpportunityRadar
    RadarFilters / RadarSummary / OpportunityList / OpportunityRow
    DispositionDialog / ValidationSummary
  CaseIntelligence
    CaseHeader / EvidenceSummary / ContradictionList
    SourceTimeline / EvidenceTaskQueue / CameraContext
    ComplianceGate / DecisionHistory
  PlatformStatus
  Shared: AsyncState, PermissionBoundary, SourceCitation,
          ConfidenceLabel, StaleDataNotice, ConfirmActionDialog
```
API contracts must be versioned, typed, and validated at runtime. Sensitive actions require server authorization and immutable audit receipts. Design deliverables: Figma tokens/components, responsive wireframes, all state variants, clickable attorney task prototype, accessibility annotations, developer handoff and test cases.

## 14. Definition of done
The UI/UX is ready for production review only when:
- all P0 journeys pass in staging against real API contracts;
- role permissions and high-risk actions are adversarially tested;
- no critical accessibility issues remain;
- usability testing shows attorneys can complete the core tasks with evidence-backed reasoning;
- CI/frontend build/E2E tests pass;
- loading, error, partial failure and stale-data states are exercised;
- legal/compliance reviewers approve relevant wording and contact boundaries.

This file is a **design specification and prioritized implementation plan**, not evidence that the application currently meets these conditions.
