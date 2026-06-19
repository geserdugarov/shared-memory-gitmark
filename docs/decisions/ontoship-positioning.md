---
node_type: decision
title: OntoShip positioning — team experience-transfer for AI-agent dev
service: _platform
status: active
updated: 2026-06-18
tags: [positioning, strategy, dev-flow, handoff, adr]
links:
  relates_to: [../reference/architecture.md, ../services/dev-flow/README.md, ../services/gitmark-cli/README.md]
  depends_on: [metrics.md]
---

# Decision: what OntoShip is for

> ADR capturing an external review of OntoShip and the resulting positioning call.
> Recorded so the conclusion is enforced, not re-argued from scratch.

## Context

OntoShip drew a substantive review. The useful part, stripped of the argument:
the project is **not** a research contribution and **not** a new search method — it is an
opinionated engineering product in three layers, with value spread unevenly across them:

1. **KB** — markdown as source of truth + regenerated artifacts (index / HTML / graph).
   Simple, honest, deterministic.
2. **Search** (FTS5 + trigram) — the weakest layer on the merits. On semantic recall a
   vector index wins. This is an accepted ceiling, not an edge.
3. **Workflow** — `dev-flow` (spec → worktree → review → ship) + `destructive-guard`.
   **This is the actual product**, and it's the layer the review never looked at.

The debate circled layer 2 (search); the real advantage is layer 3 — a **repeatable,
gated "operator + agent → PR" flow**. The wrong altitude was being defended.

## Decision

**OntoShip's goal: a tool that lets the team transfer the operating method for building
with AI agents.** It is internal **team enablement / experience-transfer**, not OSS-for-stars
and not sellable IP.

Concretely, OntoShip exists so an operator (teammate, or someone receiving a handed-off
"vibecoded" project) can pick up a repo and drive work to a PR with an agent — the way the
author would — without the author in the loop. The KB is the substrate that makes this
possible (a deterministic md source any human or agent can read); the dev-flow is the
method being transferred.

### Positioning consequences

- **Sell it as a ship-flow + operator-handoff over plain markdown — not as a search engine.**
- Layer 1 (md-as-truth + regeneration) is the honest architectural foundation: the source
  is deterministic; only the curator *agent* on top is non-deterministic. Keep it.
- Layer 2 (FTS5): state the boundary plainly — "good enough for ~hundreds of docs with an
  agent as the consumer." Don't claim search superiority.
- Layer 3 (dev-flow + guard) is where investment and the story go.

## What is genuinely strong (keep leaning on it)

- **Radical simplicity as an operational property** (zero-dep / offline / stdlib /
  deterministic) — lets the tool drop into any client repo, any CI, any operator's hands
  with no model or GPU. Directly serves the handoff use-case.
- **md-as-source-of-truth + regeneration** — clean answer to "non-deterministic source of
  truth": the source is deterministic; only the curator agent is not.
- **Proof by existence** — products maintained with this approach. For an engineering tool
  this is valid fitness-for-purpose evidence (survival test), not salesmanship.

## Valid criticism to address (accepted)

1. **No defined/measured metric** — the #1 gap. Without it there's no optimization target.
   → see [metrics.md](metrics.md). Reframed around *transfer*, not search quality.
2. **No related-works / positioning** — vs graphify / OKF / agents.md / skills. Add to
   README (convergent evolution, when-to-use). *Lower priority given the internal goal,
   but still the honest framing.*
3. **Structure is manual** — an AST-scaffold (skeleton derived from code, agent writes the
   prose) would close this and matches the "let the agent do everything" intent.
   → prototype `gitmark scaffold`.
4. **FTS5 ceiling is real** — fine at ~100 docs + agent consumer; declare it as a conscious
   boundary, not "best in class."

## Where the review overreached (noted, not adopted)

Treated the optional ontology as mandatory; called `lint` overhead (it's invariant
enforcement); "FTS = a crutch for bad structure" is too absolute; and judged an engineering
tool by scientific falsifiability (category error). Strong on the merits, but reviewed one
layer and hung the verdict on the whole.

## Next actions (priority order)

1. **Define + measure the transfer metric** on 3 projects — see [metrics.md](metrics.md).
2. **Related-works** paragraph in README (graphify / OKF / agents.md / skills).
3. **AST-scaffold prototype** (`gitmark scaffold`) so structure is derived, not hand-authored.
