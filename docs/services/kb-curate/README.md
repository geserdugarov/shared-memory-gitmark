---
node_type: service
title: kb-curate — KB maintenance skill
service: kb-curate
status: active
updated: 2026-06-16
tags: [ontology, curation, documentation, skill]
links:
  documents: [../../../skills/kb-curate/SKILL.md]
  depends_on: [../../ontology.md]
  relates_to: [../gitmark-cli/README.md]
---

# kb-curate — KB maintenance skill

`kb-curate` is the skill that keeps the markdown knowledge base healthy. It does not
search the KB or render it — it governs how docs are **added, edited, moved, and deleted**
so the collection stays a typed ontology instead of decaying into a pile of files.

The semantic model it enforces lives in [`docs/ontology.md`](../../ontology.md): every
`.md` document is a typed **object** (`node_type`) with **properties** (frontmatter) and
**typed links** — the Palantir-Foundry idea applied to documentation over code. This skill
is the **operational checklist** that puts that model into practice. Principle: *md+git is
the source of truth, with an ontology on top.*

## When it triggers

Apply the skill on any documentation mutation:

- **Add** a doc ("add a doc", "record a decision", "write a runbook").
- **Edit** a doc whose meaning changed, or whose status changed.
- **Move / reorganize** docs across folders.
- **Delete** a doc.

Before writing anything, search first (`gitmark.py search "<topic>"`). If the topic
already exists, **edit the existing doc** rather than creating a duplicate.

## The curation actions it codifies

These map to the kinetic layer ("Actions") of the ontology.

### CREATE (adding knowledge)

1. **Classify the `node_type`** — pick one type for the doc. Rule of thumb when unsure:
   a spec is `reference`, a how-to is `guide`.
2. **Place it in the right folder** — type drives location: service-specific →
   `docs/services/<svc>/`; cross-cutting → `docs/reference/`; ops procedure → `docs/ops/`;
   plan → `docs/plans/`; decision → `docs/decisions/`.
3. **Add frontmatter** — minimum `node_type`; for load-bearing docs also `title`,
   `service`, `status: active`, `updated: YYYY-MM-DD`.
4. **Add typed links** — at least one, to code (`documents` / `implemented_by`) or to a
   sibling doc (`depends_on` / `relates_to`). No orphans.
5. **Index it** — add a line to the folder's `README.md`: `- [Title](file.md) — hook`.

### UPDATE (editing)

- Meaning changed → bump `updated:`.
- Doc went stale → set `status: deprecated` and put `supersedes: [old.md]` on the
  replacement.
- Junk → delete it (git keeps the history).

### MOVE (reorganizing)

- `git mv` to preserve history, then **rewrite every link** to the doc and update the
  `README.md` indexes of both the source and destination folders.

### DEPRECATE

- Set `status` to `deprecated`/`archived` and record the replacement via `supersedes`.

### LINK — no orphans

- Every load-bearing doc must have at least one incoming or outgoing typed link.

### REINDEX — always at the end

```bash
python3 <plugin>/skills/kb-search/gitmark.py lint     # invariants I1–I6
python3 <plugin>/skills/kb-search/gitmark.py index    # rebuild search
```

`lint` flags missing/broken frontmatter, types outside the vocabulary, orphans, broken
links, and folders without a README. Fix until clean.

## The vocabularies it enforces (brief)

The skill never invents values — it draws from fixed vocabularies defined in the ontology:

- **`node_type`**: `service` · `reference` · `runbook` · `gotcha` · `decision` · `plan` ·
  `guide` · `report` · `index`.
- **Link types**: `documents` · `depends_on` · `supersedes` · `relates_to` ·
  `implemented_by` · `part_of`.
- **`status`**: `active` · `draft` · `deprecated` · `archived`.
- **`service`**: a controlled vocabulary defined per project.

See [`docs/ontology.md`](../../ontology.md) for the full type/link/property tables and the
`gitmark lint` invariants (I1–I6) — this README intentionally does not duplicate them.
