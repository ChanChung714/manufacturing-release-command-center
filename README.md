# manufacturing-release-command-center
A synthetic decision-support prototype that converts fragmented manufacturing quality records into release-readiness recommendations, next-best-action prioritization, and what-if operational simulations.

## Why I Built This

I built this project as a proof-of-thinking prototype for a Palantir Deployment Strategist / Warp Speed style role. The goal was not to build a validated QA release system, but to demonstrate how I would approach a messy manufacturing deployment problem: identify the high-value operational decision, map fragmented records into common objects, define decision logic, create role-specific workflows, and communicate projected operational impact.

This project reflects my background in regulated manufacturing, quality systems, CAPA, change control, training, supplier quality, and cross-functional workflow design. It is intended to show how those domain skills can translate into a data-enabled deployment use case.

## Problem Statement

Manufacturing release readiness is often fragmented across MES/ERP, QMS/eQMS, LMS, supplier quality, and environmental monitoring systems.

QA and Operations teams may struggle to quickly determine which lots can release, which are blocked, and what action should be taken first. Static reports or spreadsheets can show status, but often do not explain operational impact, evidence, or next-best actions.

## What the Prototype Does

- Loads synthetic manufacturing quality data across 250 lots.
- Connects lots, suppliers, deviations, CAPAs, change controls, training records, and release blockers.
- Calculates readiness score and recommended status.
- Separates hard blockers from review drivers.
- Provides executive overview, lot drilldown, control tower, action queue, decision simulator, and architecture/data model views.
- Simulates operational interventions and projects release impact.

## Dataset

- All data is synthetic and representative only.
- 250 synthetic lots
- 5 plants
- 25 products
- 40 suppliers
- 120 deviations
- 45 CAPAs
- 30 change controls
- 300 training records

## Key Baseline Results

| Metric | Value |
|---|---:|
| READY | 45 |
| REVIEW | 86 |
| HOLD | 45 |
| BLOCKED | 74 |
| Average score | 65.76 |

## Decision Simulator Example

### Default Simulation

- Resolve all missing COA issues
- Approve or disposition open validation-required changes

### Projected Result

| Metric | Value |
|---|---:|
| Blocked before | 74 |
| Blocked after | 44 |
| Moved out of BLOCKED | 30 |
| READY increase | 22 |

This matters because the app does not simply show that lots are blocked; it estimates which interventions reduce blocked lots and increase release readiness.

## Architecture / Data Model

The prototype maps fragmented source-system records into canonical operational objects and decision outputs.

### Source Systems

- MES / ERP
- QMS / eQMS
- LMS
- Supplier Quality
- LIMS / Environmental Monitoring
- Manual QA Review

### Canonical Objects

- Plant
- Product
- Supplier
- Lot
- Deviation
- CAPA
- Change Control
- Training Record
- Release Decision

### Decision Outputs

- Readiness Score
- Recommended Status
- Hard Blockers
- Review Drivers
- Next Best Action
- Projected Release Impact
- Decision Rationale

### Workflow Map

```text
Source Systems -> Canonical Objects -> Scoring Logic -> Decision Recommendation -> Action Queue -> Simulation / Next Best Action
```

## User Workflows

- QA Manager: reviews blocked lots, evidence, hard blockers, and release rationale.
- Plant / Operations Leader: prioritizes batch record, deviation, and operational actions.
- Supplier Quality: identifies supplier-driven release risk and missing COA issues.
- Training Owner: closes overdue training tied to validation-required changes.
- Change Control Board: dispositions validation-required changes affecting release readiness.
- Executive stakeholder: monitors release posture, plant-level risk, and impact of interventions.

## Field Learning and Product Backlog

### Observed Friction

- Users need explanation when a simulation does not reduce blocked lots.
- QA needs blocker rationale separated from review drivers.
- Executives need impact, not just counts.
- Users need role-specific action queues.

### Product Backlog

- Role-based task assignment
- Audit trail for disposition rationale
- Writeback to QMS/MES/LMS
- Validated release control integration
- AIP-style assistant for release meeting briefs
- Source-system refresh and exception monitoring

## Deployment Roadmap

- Phase 1: Validate object model and blocker logic with QA/Ops using one plant/product family.
- Phase 2: Connect real MES/QMS/LMS/supplier data sources.
- Phase 3: Add role-based workflows, task assignment, and release meeting brief.
- Phase 4: Add controlled writeback, audit trail, and validation controls.
- Phase 5: Scale to additional plants and product families.

## How to Run

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Limitations

- Synthetic data only.
- Not a validated QA release system.
- Does not replace QA release authority.
- Does not write back to QMS/MES/LMS.
- Logic would need validation with SMEs and quality procedures before production use.

## Demo Talking Points

- The central decision is which lots can release, which are blocked, and what QA/Ops should do first.
- The prototype maps fragmented manufacturing records into canonical objects such as Lot, Supplier, Deviation, CAPA, Change Control, and Training Record.
- The Decision Simulator shows that resolving missing COAs and dispositioning validation-required changes moves 30 lots out of BLOCKED and increases READY lots by 22.
- The Action Queue and Next Best Action ranking translate analysis into operational priorities.
- The prototype is synthetic and not a validated release system, but it demonstrates how a deployment workflow could be scoped, prototyped, and expanded.

## Relevance to Palantir Warp Speed / Deployment Strategist Role

This project demonstrates the ability to:

- Identify a high-value manufacturing operational decision.
- Map fragmented datasets into operational objects.
- Build a working prototype.
- Support user-specific workflows.
- Explain evidence behind recommendations.
- Simulate operational interventions.
- Communicate executive impact.

The intent is to show how domain expertise in regulated manufacturing and quality systems can be translated into deployment strategy, data modeling, workflow design, and executive decision support.
