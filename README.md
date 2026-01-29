G-CCI AI Intake MVP

Global Case Confidence & Intelligence Platform

A lawyer-centric AI decision system for catastrophic Personal Injury and Trucking litigation.

Overview

The G-CCI Platform (Global Case Confidence & Intelligence) is an AI-powered decision-support system designed to eliminate lead noise and surface high-value litigation opportunities before a human lawyer ever engages.

This MVP demonstrates how real-time data, explainable AI, and litigation-aware scoring can:

Prioritize catastrophic truck and severe PI claims

Forecast case value and confidence

Explain why a case is elite (SHAP-style attribution)

Enforce compliance and advertising rules

Provide live triage, alerts, and auditability

This system is calibrated for high-stakes, truck-dominant PI firms such as The Graham Firm (“Big Truck Lawyers”).

Core Capabilities
1. Predictive Acquisition (“Radar”)

Scans public data (police blotters, forums, geo-signals)

Identifies high-risk crash zones

Captures structured intake via AI voice agents

2. Case Valuation & Triage (“The Brain”)

Lead Confidence Score (0–100)

Expected Case Value ($50K – $5M+)

Truck vs Non-Truck submodel routing

SHAP-style liability and damage attribution

3. Explainability & Trust

Feature contribution bars

Plain-English legal reasoning

Model path disclosure

Compliance trace (RAG + filters)

4. Predictive Ops Center

Attorney matching by venue and case class

Telematics / EDR enrichment

Live alert stream (CRITICAL / WARN / INFO)

MVP Architecture
Frontend (HTML / JS Dashboard)
        |
        v
FastAPI Backend
  ├── /intake
  ├── /score
  ├── /explain
  └── /compliance-trace
        |
        v
AI Decision Orchestrator
  ├── Truck Submodel
  ├── Non-Truck PI Submodel
  ├── Case Value Engine
  └── SHAP Explainability
        |
        v
RAG + Compliance Layer
  ├── GA Tort Law
  ├── FMCSA Regulations
  ├── GA Trucking Case Law
  └── Advertising & Ethics Filters

API Endpoints
Endpoint	Description
POST /intake	Accepts and stores raw lead data
POST /score	Returns LeadScore + Value Estimate
POST /explain	Returns SHAP + Plain-English reasoning
POST /compliance-trace	Returns sources + filters applied
Repository Structure
app/
 ├── app.py           # FastAPI entrypoint
 ├── engine.py       # Scoring + routing logic
 ├── schemas.py      # Pydantic models
 ├── explain.py      # SHAP-style reasoning
 ├── compliance.py   # RAG + rules filters
 └── store.py        # Intake persistence

frontend/            # HTML UI
docs/                # Research + legal corpus
assets/              # UI images and logos
Strategic Vision

G-CCI is not a dashboard.
It is a revenue intelligence engine for catastrophic litigation.

It proves:

AI prioritization

Revenue-weighted decisioning

Litigation-aware explainability

Compliance-first automation

To stakeholders, this system behaves like a live production platform, not a mockup.

Roadmap

Live public data ingestion (GDOT, NHTSA, police)

Real SHAP from trained XGBoost model

Mapbox crash heatmaps

FMCSA violation overlays

CRM + call routing automation

Author: Abraham Gilbert
License: Proprietary MVP Prototype

