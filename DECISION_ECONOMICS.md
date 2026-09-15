# G-CCI Decision Economics Layer

## Objective

The Decision Economics view translates G-CCI's analytical activity into attorney-facing operational and economic metrics without presenting modeled projections as observed firm outcomes.

## Metric classes

### Measured
Derived directly from data the system currently holds. In the present React demonstration these values are synthetic fixture counts, not production firm results.

- Qualified Case Opportunities
- Qualification rate
- Evidence Gaps Identified
- Share of opportunities with evidence gaps
- Tier A/B/C distribution
- Contradictions forcing review

### Modeled
Computed from explicit user-adjustable assumptions.

- Attorney-review hours avoided
- Modeled newly signed cases
- Blended average expected case value
- Incremental expected case value

These metrics must never be represented as observed outcomes.

### Not yet measurable
Requires attorney disposition and downstream case outcome data.

- False-positive rate
- Real sign-rate lift
- Real incremental recoveries
- Real review-time reduction

## Current modeled assumptions

The dashboard exposes the following assumptions as sliders rather than hiding them inside a black box:

- manual review minutes per raw lead
- percentage of review effort removed by pre-screening
- modeled sign-rate lift
- average Tier A case value
- average Tier B case value

## Architecture

The React application now lives under `frontend-react/` on the canonical TypeScript integration branch. It contains two primary views:

1. **Decision Economics** — the transparent measured/modeled economics dashboard.
2. **Platform Status** — reads the live TypeScript runtime's `/api/ontology` and `/api/ledger/integrity` endpoints.

The frontend intentionally does not depend on the older FastAPI `/api/incidents` contract from the historical React branch.

## Future runtime integration

The synthetic economics fixture should eventually be replaced by a TypeScript endpoint that aggregates decision-ledger and opportunity events. The preferred contract should separately return:

- measured counters and time series
- outcome availability state
- model assumptions/version
- modeled results
- provenance references for each measured metric

False-positive rate should remain unavailable until a real attorney disposition event is written back to the decision ledger.

## QA boundary

CI now contains separate jobs for:

- TypeScript backend compile
- React/Vite frontend build
- RDF/OWL/SHACL ontology validation

GitHub Actions currently exhibits an infrastructure-level failure where jobs terminate without exposed steps and job-log retrieval returns `BlobNotFound`. This is not being treated as a passing build. The feature remains in testing until an observable green build is available.
