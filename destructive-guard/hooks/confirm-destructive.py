#!/usr/bin/env python3
"""Claude Code PreToolUse hook (matcher: Bash) — ДЕТЕКТ удаления → запрос y/n.

В отличие от block-destructive.py (тот делал exit 2 = глухой блок), этот хук на
деструктивной команде возвращает permissionDecision:"ask" → Claude Code показывает
интерактивное подтверждение (y/n) ДАЖЕ в bypassPermissions (explicit ask переживает
bypass). На обычных командах — молча пропускает (exit 0, без решения).

Severity-тиринг для bypass: каждый детект помечается уровнем — CRITICAL
(необратимо или бьёт за пределы рабочей копии) или ORDINARY (локальное удаление
файлов, обратимое). В режиме permission_mode=="bypassPermissions" хук поднимает
y/n ТОЛЬКО на CRITICAL, ORDINARY проходит молча (раз пользователь явно ушёл в
bypass). Во всех остальных режимах — ask на любой детект, как раньше.

CRITICAL: rm -r/-rf (кроме регенерируемых ./build|dist|node_modules…); rm по
/, ~, *, абс./системным путям; shred/srm; dropdb; find -delete/-exec rm;
git reset --hard|clean -f|push --force|branch -D; docker prune|volume rm|
compose down -v; SQL DROP/TRUNCATE/DELETE FROM.
ORDINARY: rm <file> без -r; rmdir|unlink|truncate; git rm; docker rm/rmi,
(image|network|container) rm.

Детект — по токенам (split по ; && || | & ( ) `, первый токен каждой простой
команды), поэтому `perform`/`transform`/`terraform` НЕ ловятся.

Ловит: rm rmdir shred unlink srm truncate dropdb; find -delete/-exec rm|unlink|
shred|srm|rmdir; git rm|clean|reset --hard|push --force/-f|branch -D; docker rm/
rmi, (volume|image|system|network|container|builder) prune, (volume|image|network|
container) rm, compose down -v; docker-compose down -v; SQL DROP/TRUNCATE/DELETE
FROM при наличии db-клиента.

Закрытые обходы (см. живой red-team):
- `\\rm`, `\\git` — снимаем ведущий backslash-эскейп с имени программы;
- `git -C path reset`, `git -c k=v rm`, `git --git-dir=… reset` — пропускаем
  глобальные опции git перед сабкомандой;
- `docker --context prod rm`, `docker -H host rmi` — то же для docker;
- `bash -c "rm …"`, `sh -c '…'`, `bash -lc "…"` — рекурсивно разбираем строку -c;
- `… | xargs rm`, `xargs -0 rm` — разбираем команду, которую запускает xargs.

ВНЕ охвата Bash-слоя (деструктив внутри файла/скрипта, токен-парсер его не видит):
`python x.py`/`os.remove`, `node x.js`/`unlinkSync`, `psql -f file.sql`, `bash x.sh`.
Их частично прикрывает встроенный guard Claude Code. НЕ ловим, чтобы не флажить
любой запуск интерпретатора (это убило бы signal-to-noise гарда).

НЕ трогает: '>' редиректы, docker compose down без -v, git push --force-with-lease.
"""
import os
import sys
import json
import re
import subprocess

# Звук/уведомление при детекте можно отключить: NDG_NOTIFY=0
_NOTIFY = os.environ.get("NDG_NOTIFY", "1") != "0"
# Имя системного звука macOS (Funk/Sosumi/Basso/Glass/Ping/Hero...). NDG_SOUND.
_SOUND = os.environ.get("NDG_SOUND", "Funk")

DB_CLIENTS = r'\b(psql|mysql|mariadb|mongosh|mongo|clickhouse-client|clickhouse|sqlite3|dropdb)\b'
PREFIXES = {"sudo", "command", "time", "env", "nohup", "builtin", "exec",
            "then", "do", "else", "{", "(", "!"}
DESTRUCTIVE = {"rm", "rmdir", "shred", "unlink", "srm", "truncate", "dropdb"}
SHELLS = {"sh", "bash", "zsh", "dash", "ash", "ksh", "fish"}

# Уровни критичности (для bypass-тиринга, см. docstring).
CRIT = "critical"
ORD = "ordinary"
# Режимы Claude Code, где Bash выполняется без промпта → ослабляем фильтр до CRIT.
RELAXED_MODES = {"bypassPermissions"}
# Регенерируемые локальные каталоги: рекурсивный rm по ним — ORDINARY.
REGEN_DIRS = {"build", "dist", "node_modules", ".next", "target", "coverage",
              "out", ".cache", "tmp", ".pytest_cache", "__pycache__", ".turbo",
              ".parcel-cache", ".nuxt", ".svelte-kit", ".gradle", "bin", "obj"}

# Глобальные опции, забирающие отдельный токен-значение (форма `--opt val`).
# Форма `--opt=val` распознаётся отдельно (по наличию '=').
GIT_VALUE_OPTS = {"-C", "-c", "--git-dir", "--work-tree", "--namespace",
                  "--super-prefix", "--exec-path"}
DOCKER_VALUE_OPTS = {"--context", "-H", "--host", "--config", "--log-level",
                     "-l", "--tlscacert", "--tlscert", "--tlskey"}
XARGS_VALUE_OPTS = {"-I", "-i", "-n", "-P", "-d", "-s", "-a", "-E", "-L",
                    "--max-procs", "--max-args", "--delimiter", "--arg-file",
                    "--max-lines", "--replace", "--max-chars"}


def _alert(reason: str):
    """Звук + баннер-уведомление (macOS) + терминальный BEL. Fire-and-forget,
    stdout НЕ трогаем (там только JSON-решение хука)."""
    if not _NOTIFY:
        return
    # BEL в stderr — если в терминале включён visual bell, экран мигнёт
    try:
        sys.stderr.write("\a")
        sys.stderr.flush()
    except Exception:
        pass
    if sys.platform != "darwin":
        return
    safe = reason.replace('"', "'")[:180]
    try:
        # display notification = баннер + звук одним вызовом
        subprocess.Popen(
            ["osascript", "-e",
             f'display notification "{safe}" with title "🛡️ Команда на удаление" sound name "{_SOUND}"'],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
        # дублируем звук afplay (на случай если уведомления приглушены)
        snd = f"/System/Library/Sounds/{_SOUND}.aiff"
        if os.path.exists(snd):
            subprocess.Popen(["afplay", snd],
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception:
        pass


def proceed():
    # никакого решения — дальше решают permission-правила (в bypass = выполнить)
    sys.exit(0)


def ask(reason: str):
    _alert(reason)
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "ask",
            "permissionDecisionReason": f"⚠️ Команда на удаление — подтвердите: {reason}",
        }
    }))
    sys.exit(0)


def _strip_opts(args, value_opts):
    """Срезать ведущие опции (всё, что начинается с '-'), вернуть остаток —
    первый позиционный аргумент (сабкоманда / запускаемая программа) и далее.
    Опции из value_opts забирают следующий токен как своё значение."""
    j = 0
    while j < len(args) and args[j].startswith("-"):
        a = args[j]
        if "=" in a:
            j += 1
        elif a in value_opts:
            j += 2
        else:
            j += 1
    return args[j:]


def _unquote(s: str) -> str:
    s = s.strip()
    for q in ('"', "'"):
        if len(s) >= 2 and s[0] == q and s[-1] == q:
            return s[1:-1]
    # частичная кавычка (top-level split мог разорвать строку) — снимаем края
    return s.strip('"').strip("'")


def _norm_target(t: str) -> str:
    t = t.rstrip("/")
    if t.startswith("./"):
        t = t[2:]
    return t


def _rm_severity(args) -> str:
    """CRIT/ORD для `rm`: рекурсия или опасная цель → critical; одиночные файлы
    и регенерируемые ./build|dist|node_modules… → ordinary."""
    flags = [a for a in args if a.startswith("-")]
    targets = [a for a in args if not a.startswith("-")]
    for t in targets:
        tt = t.rstrip("/")
        if (tt in ("", "/", "~", "*", ".", "..")
                or tt.startswith(("/", "~", "$"))
                or "*" in tt or ".." in tt):
            return CRIT
    recursive = (any("r" in f.lower() for f in flags if not f.startswith("--"))
                 or "--recursive" in flags)
    if recursive:
        norm = [_norm_target(t) for t in targets]
        if targets and all(n in REGEN_DIRS for n in norm):
            return ORD
        return CRIT
    return ORD


def detect(cmd: str, _depth: int = 0):
    """Вернуть (severity, reason) если команда деструктивная, иначе None."""
    if _depth > 4 or not cmd.strip():
        return None

    low = cmd.lower()
    if re.search(DB_CLIENTS, low):
        if (re.search(r'\bdrop\s+(table|database|schema)\b', low)
                or re.search(r'\btruncate\b', low)
                or re.search(r'\bdelete\s+from\b', low)):
            return (CRIT, f"SQL-удаление данных: {cmd.strip()}")

    segments = re.split(r'\|\||&&|\$\(|[;\n|&()`]', cmd)
    for seg in segments:
        s = seg.strip()
        if not s:
            continue
        toks = s.split()
        i = 0
        while i < len(toks):
            t = toks[i]
            if re.match(r'^[A-Za-z_][A-Za-z0-9_]*=', t):
                i += 1
                continue
            if t.split("/")[-1].lstrip("\\") in PREFIXES:
                i += 1
                continue
            break
        if i >= len(toks):
            continue
        # имя программы: убрать путь и снять ведущий backslash-эскейп (`\rm` → `rm`)
        prog = toks[i].split("/")[-1].lstrip("\\")
        args = toks[i + 1:]

        if prog in DESTRUCTIVE:
            if prog == "rm":
                return (_rm_severity(args), f"удаление: {s}")
            if prog in ("shred", "srm", "dropdb"):
                return (CRIT, f"удаление: {s}")
            return (ORD, f"удаление: {s}")  # rmdir, unlink, truncate

        if prog == "find" and re.search(
                r'(^|\s)(-delete\b|-(exec|execdir|ok|okdir)\s+(rm|unlink|shred|srm|rmdir)\b)',
                " " + " ".join(args)):
            return (CRIT, f"find-удаление: {s}")

        if prog == "git" and args:
            ga = _strip_opts(args, GIT_VALUE_OPTS)
            if ga:
                head = ga[0]
                rest = ga[1:]
                if head == "rm":
                    return (ORD, f"git rm: {s}")
                if head == "clean":
                    sev = CRIT if any("f" in f for f in rest if f.startswith("-")
                                      and not f.startswith("--")) or "--force" in rest else ORD
                    return (sev, f"git clean: {s}")
                if head == "reset" and "--hard" in rest:
                    return (CRIT, f"git reset --hard: {s}")
                if head == "push" and any(
                        a in ("--force", "-f") or a.startswith("+") for a in rest):
                    return (CRIT, f"git push --force: {s}")
                if head == "branch" and "-D" in rest:
                    return (CRIT, f"git branch -D: {s}")

        if prog in ("docker", "podman") and args:
            da = _strip_opts(args, DOCKER_VALUE_OPTS)
            if da:
                if da[0] in ("rm", "rmi"):
                    return (ORD, f"docker {da[0]}: {s}")
                if len(da) >= 2 and da[1] == "prune" and da[0] in (
                        "volume", "image", "system", "network", "container", "builder"):
                    return (CRIT, f"docker {da[0]} prune: {s}")
                if len(da) >= 2 and da[0] in (
                        "volume", "image", "network", "container") and da[1] == "rm":
                    sev = CRIT if da[0] == "volume" else ORD
                    return (sev, f"docker {da[0]} rm: {s}")
                if da[0] == "compose" and "down" in da and any(
                        a in ("-v", "--volumes") for a in da):
                    return (CRIT, f"docker compose down -v: {s}")

        if prog == "docker-compose" and "down" in args and any(
                a in ("-v", "--volumes") for a in args):
            return (CRIT, f"docker-compose down -v: {s}")

        # bash/sh -c "…": разобрать строку-скрипт рекурсивно
        if prog in SHELLS and args:
            ci = None
            for k, a in enumerate(args):
                if a == "-c" or re.match(r'^-[A-Za-z]*c$', a):
                    ci = k
                    break
            if ci is not None and ci + 1 < len(args):
                inner = _unquote(" ".join(args[ci + 1:]))
                r = detect(inner, _depth + 1)
                if r:
                    return r

        # xargs CMD: разобрать команду, которую запускает xargs
        if prog == "xargs" and args:
            rest = _strip_opts(args, XARGS_VALUE_OPTS)
            if rest:
                r = detect(" ".join(rest), _depth + 1)
                if r:
                    return r

    return None


def main():
    try:
        data = json.load(sys.stdin)
    except Exception:
        proceed()

    cmd = ((data.get("tool_input") or {}).get("command") or "")
    if not isinstance(cmd, str) or not cmd.strip():
        proceed()

    result = detect(cmd)
    if result:
        severity, reason = result
        mode = data.get("permission_mode") or ""
        # в bypass поднимаем y/n только на CRITICAL; ORDINARY проходит молча
        if mode in RELAXED_MODES and severity != CRIT:
            proceed()
        ask(reason)
    proceed()


if __name__ == "__main__":
    main()
