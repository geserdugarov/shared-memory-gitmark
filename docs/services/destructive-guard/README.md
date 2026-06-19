---
node_type: service
title: destructive-guard — confirm destructive commands
service: destructive-guard
status: active
updated: 2026-06-16
tags: [hook, safety, pretooluse, security]
links:
  documents: [../../../destructive-guard/hooks/confirm-destructive.py, ../../../destructive-guard/hooks/hooks.json]
  implemented_by: [../../../destructive-guard/hooks/confirm-destructive.py]
---

# destructive-guard

A Claude Code **PreToolUse hook** that intercepts destructive shell commands and turns
them into an interactive **y/n confirmation** before they run. It is a single
stdlib-only Python script — no dependencies. Source:
[confirm-destructive.py](../../../destructive-guard/hooks/confirm-destructive.py).

The guard never *blocks* a command outright (no `exit 2`); instead it returns
`permissionDecision: "ask"`, so Claude Code surfaces a y/n prompt. On safe commands it
exits silently (`exit 0`, no decision) and lets normal permission rules decide.

## How the hook is wired

[hooks.json](../../../destructive-guard/hooks/hooks.json) registers one hook:

- Event: **`PreToolUse`**
- Matcher: **`Bash`** (only Bash tool calls are inspected)
- Command: `python3 "${CLAUDE_PLUGIN_ROOT}/hooks/confirm-destructive.py"`
- Timeout: `5` seconds

The hook reads the tool-call JSON from stdin, pulls `tool_input.command`, runs `detect()`
on it, and — if destructive — emits an `ask` decision as JSON on stdout. Empty / unparsable
input proceeds silently.

## What it guards (exact detection)

Detection is **token-based**: the command is split on `; && || | & ( ) \`` and the *first
token* of each simple command is examined. Leading `VAR=val` assignments and prefixes
(`sudo`, `command`, `time`, `env`, `nohup`, `builtin`, `exec`, `then`, `do`, `else`,
`{`, `(`, `!`) are skipped. The program name is path-stripped and a leading
backslash-escape is removed (`\rm` → `rm`). Because only the leading token is matched,
look-alikes like `perform`, `transform`, `terraform` are **not** flagged.

Each detection carries a **severity** — `CRITICAL` or `ORDINARY` — used for the
bypassPermissions tiering described below.

| Category | Patterns detected | Severity |
|---|---|---|
| File deletion | `rm` (severity computed, see below); `shred`, `srm`, `dropdb` | CRITICAL |
| File deletion | `rmdir`, `unlink`, `truncate` | ORDINARY |
| find-based delete | `find … -delete`, `find … -exec\|-execdir\|-ok\|-okdir rm\|unlink\|shred\|srm\|rmdir` | CRITICAL |
| git | `git rm` | ORDINARY |
| git | `git clean` (CRITICAL if `-f`/`--force`, else ORDINARY); `git reset --hard`; `git push --force`/`-f`/`+refspec`; `git branch -D` | CRITICAL (clean conditional) |
| docker / podman | `docker rm`, `docker rmi`, `docker image\|network\|container rm` | ORDINARY |
| docker / podman | `docker volume rm`; `docker volume\|image\|system\|network\|container\|builder prune`; `docker compose down -v\|--volumes` | CRITICAL |
| docker-compose | `docker-compose down -v\|--volumes` | CRITICAL |
| SQL | `DROP TABLE\|DATABASE\|SCHEMA`, `TRUNCATE`, `DELETE FROM` — only when a DB client (`psql`, `mysql`, `mariadb`, `mongosh`, `mongo`, `clickhouse-client`, `clickhouse`, `sqlite3`, `dropdb`) appears in the command | CRITICAL |

### `rm` severity logic (`_rm_severity`)

- **CRITICAL** if any target is a dangerous path: empty, `/`, `~`, `*`, `.`, `..`, or
  starts with `/` `~` `$`, or contains `*` or `..`.
- Otherwise, if recursive (`-r`/`-R`/`--recursive`): **CRITICAL**, *unless* every target is
  a regenerable directory — then **ORDINARY**. Regenerable set: `build`, `dist`,
  `node_modules`, `.next`, `target`, `coverage`, `out`, `.cache`, `tmp`, `.pytest_cache`,
  `__pycache__`, `.turbo`, `.parcel-cache`, `.nuxt`, `.svelte-kit`, `.gradle`, `bin`, `obj`
  (targets normalized by stripping trailing `/` and leading `./`).
- Otherwise (non-recursive single-file `rm`): **ORDINARY**.

### Closed bypasses (red-team hardened)

- `\rm`, `\git` — leading backslash-escape stripped from the program name.
- `git -C path …`, `git -c k=v …`, `git --git-dir=… …` — leading git global options
  (incl. value-taking `-C`, `-c`, `--git-dir`, `--work-tree`, `--namespace`,
  `--super-prefix`, `--exec-path`) skipped before reading the subcommand.
- `docker --context prod rm`, `docker -H host rmi` — same global-option stripping for
  docker (`--context`, `-H`/`--host`, `--config`, `--log-level`/`-l`, TLS opts).
- `bash -c "rm …"`, `sh -c '…'`, `bash -lc "…"` — the `-c` script string is unquoted and
  re-analyzed recursively (depth-limited to 4; shells: `sh bash zsh dash ash ksh fish`).
- `… | xargs rm`, `xargs -0 rm` — the command xargs would run is parsed recursively
  (xargs value-opts like `-I -n -P -d …` skipped first).

### Explicitly NOT flagged

`>` redirects, `docker compose down` without `-v`, `git push --force-with-lease`, `mv`,
and destructive logic *inside* a file/script (`python x.py` / `os.remove`,
`node x.js` / `unlinkSync`, `psql -f file.sql`, `bash x.sh`) — the token parser does not
read file contents. These are left to Claude Code's built-in guard, deliberately, to keep
the signal-to-noise ratio high.

## Confirmation behavior

When a destructive command is detected, the hook prints a JSON decision:

```json
{"hookSpecificOutput": {"hookEventName": "PreToolUse",
  "permissionDecision": "ask",
  "permissionDecisionReason": "⚠️ Команда на удаление — подтвердите: <reason>"}}
```

Claude Code then shows a y/n prompt. Because this is an **explicit `ask`**, it survives
`bypassPermissions` — but with a **tier**:

- In `permission_mode == "bypassPermissions"`, the hook only raises the y/n prompt on
  **CRITICAL** detections; **ORDINARY** ones proceed silently (the user has explicitly
  opted into bypass for routine, reversible local deletions).
- In every other mode (`default`, etc.), **any** detection — CRITICAL or ORDINARY —
  raises the prompt.

### Sound / banner alert

On `ask`, `_alert()` fires a fire-and-forget notification (stdout stays JSON-only):

- A terminal **BEL** (`\a`) to stderr (visual-bell flash if enabled).
- On macOS only: an `osascript display notification` banner titled
  "🛡️ Команда на удаление" plus a system sound, and a duplicate `afplay` of the sound
  file (in case banner sounds are muted).
- Sound name configurable via `NDG_SOUND` (default `Funk`). Disable all alerts with
  `NDG_NOTIFY=0`.

## How it's tested

[tests/test_hook.py](../../../destructive-guard/tests/test_hook.py) is a stdlib-only
`unittest` suite that runs the real hook as a subprocess, feeds it JSON payloads, and
asserts the returned `permissionDecision`. Alerts are silenced via `NDG_NOTIFY=0`, so the
tests are safe and cross-platform. Coverage:

- `test_destructive_asks` — ~45 `ASK_CASES` spanning every category plus the closed
  bypasses (backslash, `git -C`, `bash -c`, `xargs`, docker global opts, etc.).
- `test_safe_proceeds` — `PROCEED_CASES` confirming look-alikes (`perform`/`terraform`),
  `git push --force-with-lease`, `compose down` without `-v`, redirects, `mv`, safe
  `bash -c`/`xargs`, etc. proceed silently.
- `test_empty_command_proceeds` — empty command proceeds.
- `test_bypass_critical_still_asks` — `BYPASS_CRITICAL` cases still prompt under
  `bypassPermissions`.
- `test_bypass_ordinary_proceeds_but_asks_default` — `BYPASS_ORDINARY` cases proceed
  silently under bypass but prompt in `default`.
- `test_manifests_valid_json` / `test_marketplace_source_points_to_plugin` — validate the
  plugin manifests and marketplace wiring.

Run: `python3 tests/test_hook.py` (or `python3 -m unittest -v`).
