# G-CCI Public Data Integration

## Purpose

This layer discovers and ranks **public incident opportunities**, not people. It does not identify injured persons, infer private contact information, or authorize attorney outreach. Any later identity/contact workflow remains subject to the G-CCI compliance/activation gate.

## Verified live / near-real-time sources

### GDOT 511

Official REST API. Requires a free developer key.

Configured with:

```bash
GDOT_511_API_KEY=...
```

Current runtime ingestion uses the Events endpoint. The source catalog also documents Alerts and Cameras for follow-on ingestion.

### GDOT ArcGIS

Public, no-authentication ArcGIS feature services.

Current runtime integrations:

- Unplanned Traffic Interruptions
- CCTV Camera catalog

The adapters request GeoJSON with WGS84 coordinates (`outSR=4326`).

### Waze for Cities

Waze is implemented as a **partner-feed adapter**, not as a presumed public Georgia endpoint. Enable it only when an authorized partner feed URL has been issued.

```bash
WAZE_PARTNER_FEED_URL=https://authorized-feed.example/...
WAZE_PARTNER_FEED_TOKEN=...
```

## Historical / enrichment sources

The source catalog includes NHTSA FARS and FMCSA Analysis & Information as authoritative enrichment sources. They are deliberately not represented as live incident feeds.

- NHTSA FARS: fatal-crash history / statistical enrichment.
- FMCSA A&I: commercial-carrier safety and crash-history enrichment.

Production enrichment adapters should be enabled only against a verified machine-readable endpoint or licensed export contract. No undocumented endpoint is fabricated in this build.

## API endpoints

```text
GET  /api/signals/sources
GET  /api/signals/live
POST /api/signals/live/ledger
GET  /api/signals/cameras
```

### `GET /api/signals/live`

Fetches currently enabled incident sources, normalizes them, synthesizes attorney-investigation signals, and returns source health alongside the signals.

### `POST /api/signals/live/ledger`

Performs the same fetch and writes the generated public-incident opportunity assertions to the immutable G-CCI decision ledger.

### `GET /api/signals/cameras`

Returns GDOT public CCTV camera metadata and coordinates. Snapshot/stream URLs are surfaced only when the ArcGIS source exposes them.

## Signal model

Current heuristic signal inputs include:

- commercial vehicle / truck language
- fatality language
- injury / EMS / hospital language
- full closure / major blockage
- debris, tire, or wheel-off indicators
- disabled or stalled vehicle indicators
- availability of precise coordinates

The output is an **investigation-priority signal**. It is not a liability determination, legal conclusion, client identity, or solicitation authorization.

## Safety / compliance invariant

```text
Incident Opportunity Signal
        !=
Party Identity
        !=
Contact Eligibility
        !=
Attorney Outreach Authorization
```

`OpportunitySignal.outreachPermitted` is structurally fixed to `false` in this ingestion layer.

## Environment

```bash
GDOT_511_API_KEY=
WAZE_PARTNER_FEED_URL=
WAZE_PARTNER_FEED_TOKEN=
GCCI_SOURCE_TIMEOUT_MS=8000
```

## Production hardening still required

Before continuous production polling:

1. Add durable source-event persistence and idempotency keys.
2. Add scheduled polling with per-source rate limits and backoff.
3. Store source ETags / Last-Modified values where supported.
4. Add geospatial cross-source clustering instead of only source-record deduplication.
5. Add camera-nearest-event correlation with distance/time windows.
6. Add metrics for source latency, freshness, failure rate, and duplicate rate.
7. Add verified NHTSA/FARS and FMCSA enrichment adapters once the exact machine-readable contracts are selected.
8. Obtain counsel-approved configuration for any downstream identity, solicitation, DPPA, suppression, and outreach workflows.
