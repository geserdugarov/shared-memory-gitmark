---
node_type: service
title: dev-flow — spec-driven ship pipeline
service: dev-flow
status: active
updated: 2026-06-16
tags: [dev-flow, pipeline, worktree, spec, ship]
links:
  documents: [../../../skills/dev-flow/SKILL.md, ../../../commands/ship.md]
  relates_to: [../gitmark-cli/README.md, ../kb-curate/README.md]
---

# dev-flow — spec-driven ship pipeline

`dev-flow` is OntoShip's gated pipeline for taking a feature or fix from idea to
production with an AI agent, fast and safely — typically **40 minutes to 2 hours** end
to end. The defining ideas: the **spec is plain markdown written into the KB**, the work
happens in an **isolated git worktree**, and **only green reaches prod**. The KB (the
GitMark knowledge base, see [kb-curate](../kb-curate/README.md)) is the carrier of
knowledge: onboarding, hand-off, and scaling all start from it, not from the code.

It is defined by the [`dev-flow` skill](../../../skills/dev-flow/SKILL.md) and invoked
through the [`/ship` command](../../../commands/ship.md).

## The gated pipeline

The pipeline is a sequence of stages where the later stages — review and tests — act as
**gates**: the change does not advance past a gate until it passes. Each stage produces
durable artifacts (tasks, a spec, a diff, test results) rather than throwaway state.

```
research → tasks → goal → spec → worktree → implement → tests
        → independent review → dev-tests → prod-tests → ship (MR → dev → main → prod)
```

### 1. Research
Understand the problem from **facts, not guesses**: read logs, traces, and the code
itself. Reproduce the bug or pin down the requirement before touching anything. This is
where wrong assumptions are cheapest to kill.

### 2. Tasks
Turn the research into a list of **tracked tasks with dependencies** so nothing gets
lost. Decomposition makes the scope explicit and orderable.

### 3. Goal
Crystallize **one clear goal** and a concrete **"done" criterion** from the tasks. A
single goal keeps the implementation honest and gives the gates something to check
against.

### 4. Spec
Write the spec as **markdown in the KB via [`kb-curate`](../kb-curate/README.md)** —
following the ontology: a `node_type`, frontmatter, and typed links
(`links.documents: [src/…]`) tying the spec to the code it governs. Search the KB first
(`kb-search`) so you don't duplicate an existing doc. The spec is **durable knowledge,
not a throwaway ticket**: searchable, linkable, and graphable (`gitmark map`). This is
where dev-flow builds directly on the GitMark KB — the spec becomes a first-class node
in the ontology rather than a comment that evaporates after merge.

### 5. Isolate (git worktree)
Do the work in a **dedicated `git worktree`**. `main` stays untouched, parallel agents
working on other changes don't collide, and rollback is just dropping the worktree.
Isolation is the default precisely so that experimentation is cheap and reversible.

### 6. Implement
Code to the spec inside the worktree, keeping doc↔code linked (`implemented_by`) so the
KB stays an accurate map of the codebase as the change lands.

### 7. Tests
Write or adjust **unit + E2E** tests for the feature. The test is **part of the
feature, not an afterthought** — it is the executable form of the "done" criterion.

### 8. Independent review (gate)
Run an **independent model** (e.g. Codex CLI, read-only) over the diff for logic and
security bugs before any rollout. A second model catches what the author's model
misses — on a real production codebase this pass caught **191 bugs** before they reached
prod. This is a gate because the cost of a missed logic/security bug in prod dwarfs the
cost of the review.

### 9. Dev-tests (gate)
Open an **MR with the commits into the `dev` branch** and run the **full suite** there.
Red → fix in the worktree, **don't merge**. The gate is the branch: nothing flows to
`main` until `dev` is green.

### 10. Prod-tests (gate)
Run **E2E / smoke tests against the real prod contour** — not only mocks or dev. Verify
behaviour where users actually live, because dev environments lie. This gate guards the
final merge.

### 11. Ship
Merge **`dev → main`** and deploy. Build the new image **before** stopping the old
container, then **poll the healthcheck** to measure real downtime. This ordering
minimizes the window where the service is unavailable.

## Git-flow

```
git worktree  →  MR + commits  →  dev branch (dev-tests)  →  main (prod-tests + deploy)  →  prod
```

## Why the gates

The gates — independent review, dev-tests, prod-tests — are deliberate and
non-negotiable. They are where bugs are caught before users see them; the 191-bug figure
comes specifically from the independent-review gate on a production codebase. Tests and
review are treated as **gates, not afterthoughts**, and behaviour is **verified on prod**,
not just dev.

## How it builds on the GitMark KB

The spec stage writes into the GitMark KB through `kb-curate`, so every shipped change
leaves behind an ontological document: typed, linked to its source via `documents` /
`implemented_by`, and discoverable through `kb-search` and `gitmark map`
(see [gitmark-cli](../gitmark-cli/README.md)). **md + git is the source of truth**;
everything derived — the search index, the graph — is regenerated. This is what lets
onboarding, hand-off, and scaling start from the KB rather than from reading the code.

## How a user invokes it

Run the [`/ship`](../../../commands/ship.md) command with a description of the change:

```
/ship <feature or fix description>
```

`/ship` drives the change through every stage of the pipeline, keeping the gates (tests +
independent review) and never skipping the spec. For a one-line change the stages can be
collapsed, but the gates stay — they are where the 191 bugs were caught.

## Principles

- **Spec = markdown + skills** — no ceremony, but ontological, so it stays searchable,
  linkable, and graphable.
- **Worktree isolation by default** — clean parallelism and clean rollback.
- **Tests and independent review are gates, not afterthoughts.**
- **Verify on prod**, not just dev.
- **md + git = source of truth**; everything derived is regenerated.
