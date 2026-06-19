---
node_type: reference
title: OntoShip metrics — measuring experience transfer
service: _platform
status: draft
updated: 2026-06-18
tags: [metrics, measurement, handoff, dev-flow]
links:
  depends_on: [../decisions/ontoship-positioning.md]
  relates_to: [../services/dev-flow/README.md]
---

# Metrics — what OntoShip should be measured by

> The #1 gap from review: no defined, measured metric → no optimization target.
> Per the [positioning decision](../decisions/ontoship-positioning.md), OntoShip's goal is
> **team experience-transfer for AI-agent development**, so the metrics measure *transfer
> and operator autonomy* — not search quality.

`status: draft` until baselines are collected on 3 projects.

## Primary metrics

Measure on **3 real projects** (the ones already maintained with this approach):

| Metric | Definition | Why it matters |
|---|---|---|
| **Operator onboarding time** | Calendar time from "new operator gets the repo" → their first merged PR, *without the author in the loop* | The core transfer claim: can someone pick up the method and ship? |
| **Autonomous-PR rate** | % of tasks an operator drives to PR without the author intervening | Measures whether the *method* transferred, not just one task |
| **Feature → PR time** | Time from task defined → PR opened, via the gated dev-flow | Throughput of the flow itself |

## Secondary / supporting

- **Time-to-first-answer in the KB** — operator finds the relevant doc via `/kb` instead of
  asking the author (proxy for KB self-sufficiency).
- **Re-derivation cost** — wall-clock to rebuild index + map after edits (keeps the
  "derived is cheap" promise honest).
- **Lint cleanliness** — broken links / orphans over time (KB rot indicator).

## How to collect (lightweight)

- Onboarding time / autonomous-PR rate: track per operator per project in a simple log
  (date repo handed over, date of first independent PR, tally of author interventions).
- Feature → PR time: read it off git/PR timestamps; the dev-flow already produces a PR.
- KB self-sufficiency: spot-check — did the operator ask the author something the KB
  already answers?

## What this is NOT

Not search precision/recall, not embedding-quality benchmarks. The review's pull toward
"prove the search" is the wrong target for an internal transfer tool — see the
[positioning decision](../decisions/ontoship-positioning.md).
