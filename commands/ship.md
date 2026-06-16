---
description: Run the OntoShip dev-flow — take a feature/fix from idea to production through the gated pipeline (research → tasks → goal → spec → worktree → implement → tests → review → dev-tests → prod-tests → ship).
---

Drive the change described in `$ARGUMENTS` through the **OntoShip dev-flow**.

Follow the `dev-flow` skill end to end:

1. **Research** — understand from facts (logs, traces, code); reproduce before fixing.
2. **Tasks** — decompose into tracked tasks.
3. **Goal** — crystallize one clear goal + "done" criterion.
4. **Spec** — write it as markdown in the KB via `kb-curate` (node_type, frontmatter,
   typed links `documents:[src/…]`). Search the KB first (`kb-search`) — don't duplicate.
5. **Isolate** — work in a dedicated `git worktree`.
6. **Implement** — code to the spec.
7. **Tests** — write/adjust unit + E2E.
8. **Independent review** — run an independent model (e.g. Codex CLI, read-only) over the diff.
9. **Dev-tests** — MR + commits into `dev`; run the full suite. Red → fix, don't merge.
10. **Prod-tests** — E2E/smoke against the real prod contour.
11. **Ship** — merge `dev → main` and deploy (build-before-stop + healthcheck-poll).

Keep the gates (tests + independent review). Don't skip the spec — it's the carrier of
knowledge, not a throwaway ticket.
