# GitMark Memory Bank

> A project knowledge base is just **markdown + a README index + git**. Markdown is the
> source of truth; everything derived (a search index, an HTML overview, a link graph) is
> regenerated from the md, so git stays clean. GitMark is the small toolset that makes
> that KB **searchable, navigable, and self-consistent** — and plugs into Claude Code.

Battle-tested over months of building with AI assistants: the KB that an agent (and a
human) actually wants is plain md you can read in any viewer — *plus* fast search and a
light ontology so it doesn't rot into a pile of files.

## What's in here

- **`gitmark`** — a single self-contained Python-stdlib CLI (no dependencies):
  - `index` — build a SQLite **FTS5** index: `bm25` ranking ∪ `trigram` (substring) ∪
    a fuzzy 3-gram pass (typos, morphology, non-Latin scripts). Chunked by heading.
  - `search` — ranked `file:line · heading · snippet`, `--json` for tooling.
  - `map` — a **self-contained HTML** page: file tree + rendered markdown + a radial
    **graph** of links between docs.
  - `serve` — a tiny local HTTP server to view the map.
  - `stat` — index/KB stats.
  - `lint` — checks the **code-ontology** invariants (frontmatter, vocabularies,
    orphans, broken links, missing folder READMEs).
- **A Claude Code plugin** — two skills (`kb-search`, `kb-curate`) + a `/kb` command, so
  the agent searches the KB instead of grepping, and follows curation rules when editing.
- **An ontology** (`docs/ontology.md`) — a Palantir-Foundry-style model (objects /
  properties / links) applied to documentation over code.

## Quickstart (standalone CLI)

```bash
python3 skills/kb-search/gitmark.py index            # build .gitmark/index.db
python3 skills/kb-search/gitmark.py search "auth flow"
python3 skills/kb-search/gitmark.py map -o docs-map.html
python3 skills/kb-search/gitmark.py lint             # ontology check
```

Requires Python ≥ 3.7 with SQLite **FTS5** (and ideally the **trigram** tokenizer,
SQLite ≥ 3.34, for fuzzy/substring/non-Latin matching — the tool detects it and degrades
gracefully). `.gitmark/` is a build artifact — add it to `.gitignore`.

## Install as a Claude Code plugin

```text
/plugin marketplace add vakovalskii/gitmark-memory-bank
/plugin install gitmark@gitmark-marketplace
```

Then the agent has `/kb <query>` and the `kb-search` / `kb-curate` skills. Or just copy
`skills/` and `commands/` into your repo's `.claude/` for a project-local install (no
marketplace needed).

## The methodology in one paragraph

Keep knowledge in `.md` files with a `README.md` index per folder. Give each load-bearing
doc a small **frontmatter** (`node_type`, `title`, `service`, `status`, `updated`) and at
least one **typed link** (to code or a sibling doc). Search with `gitmark search`; before
reading files at random, locate the exact spots. When you add or move docs, run
`gitmark lint` to keep it consistent and `gitmark index` to refresh search. See
[`docs/ontology.md`](docs/ontology.md).

## License

MIT — see [LICENSE](LICENSE).
