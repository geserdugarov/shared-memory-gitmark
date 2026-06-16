#!/usr/bin/env python3
"""Тесты хука confirm-destructive: кормим JSON-пейлоады, проверяем решение
(ask на удаление / молчим на безопасном). Stdlib-only, без зависимостей.

Запуск:  python3 tests/test_hook.py   (или:  python3 -m unittest -v)
Звук/баннер заглушены через NDG_NOTIFY=0, так что тесты безопасны и кросс-платформенны.
"""
import json
import os
import subprocess
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..")
HOOK = os.path.join(ROOT, "destructive-guard", "hooks", "confirm-destructive.py")

# (описание, команда, ждём_ask)
ASK_CASES = [
    ("rm file", "rm /tmp/x"),
    ("rm -rf", "rm -rf build/"),
    ("&& rm", "cd /tmp && rm foo"),
    ("sudo rm", "sudo rm -rf /var/x"),
    ("FOO=bar rm", "FOO=1 rm x"),
    ("rmdir", "rmdir olddir"),
    ("shred", "shred -u secret.key"),
    ("unlink", "unlink /tmp/link"),
    ("truncate", "truncate -s 0 file.log"),
    ("git rm", "git rm --cached f"),
    ("git clean", "git clean -fd"),
    ("git reset --hard", "git reset --hard origin/main"),
    ("git push --force", "git push --force origin main"),
    ("git push -f", "git push -f"),
    ("find -delete", "find . -name '*.tmp' -delete"),
    ("find -exec rm", "find . -name x -exec rm {} ;"),
    ("docker rm", "docker rm -f c1"),
    ("docker rmi", "docker rmi img"),
    ("docker volume rm", "docker volume rm data"),
    ("docker volume prune", "docker volume prune -f"),
    ("docker system prune", "docker system prune -a"),
    ("compose down -v", "docker compose down -v"),
    ("compose down --volumes", "docker compose down --volumes"),
    ("docker-compose down -v", "docker-compose down -v"),
    ("psql DELETE FROM", 'psql -c "DELETE FROM users"'),
    ("psql DROP TABLE", 'psql -d hub -c "DROP TABLE x"'),
    ("sqlite TRUNCATE", 'sqlite3 db "TRUNCATE TABLE t"'),
    ("subshell rm", "echo $(rm secret)"),
    # закрытые обходы (red-team D/E)
    ("backslash rm", "\\rm /tmp/x"),
    ("git -C reset --hard", "git -C /repo reset --hard"),
    ("git -c rm", "git -c core.editor=vim rm f"),
    ("git --git-dir= reset", "git --git-dir=/r reset --hard"),
    ("git branch -D", "git branch -D feature"),
    ("bash -c rm", 'bash -c "rm -rf build"'),
    ("sh -c rm", "sh -c 'rm x'"),
    ("bash -lc rm", 'bash -lc "rm x"'),
    ("xargs rm", "find . -name '*.tmp' | xargs rm"),
    ("xargs -0 rm", "find . -print0 | xargs -0 rm -rf"),
    ("xargs -I rm", "echo x | xargs -I {} rm {}"),
    ("docker --context rm", "docker --context prod rm -f c1"),
    ("docker -H rmi", "docker -H tcp://x:2375 rmi img"),
    ("find -exec unlink", "find . -name x -exec unlink {} ;"),
    ("bash -c psql delete", "bash -c \"psql -c 'DELETE FROM t'\""),
]

PROCEED_CASES = [
    ("perform/transform/confirm", 'echo "performing transform, confirm"'),
    ("terraform/warm", "npm run build && echo terraform warm"),
    ("git push normal", "git push origin main"),
    ("git push --force-with-lease", "git push --force-with-lease"),
    ("compose down (no -v)", "docker compose down"),
    ("grep DELETE FROM (no db client)", "grep -r 'DELETE FROM' src/"),
    ("redirect >", "echo hi > out.txt"),
    ("docker ps", "docker ps -a"),
    ("git status/add", "git status && git add -A"),
    ("mv not rm", "mv a b"),
    ("ls/cat", "ls -la && cat file.txt"),
    ("npm install", "npm install && npm run build"),
    # не путать с закрытыми обходами: интерпретатор/флаги без удаления
    ("bash -c safe", 'bash -c "ls -la"'),
    ("xargs cat", "ls | xargs cat"),
    ("git -C status", "git -C /repo status"),
    ("git branch list", "git branch -a"),
    ("docker --context ps", "docker --context prod ps -a"),
]


def decision(command: str, mode: str = "default") -> str:
    """Вернуть 'ask' | 'proceed' от хука для данной команды в заданном режиме."""
    payload = json.dumps({"tool_name": "Bash", "permission_mode": mode,
                          "tool_input": {"command": command}})
    env = dict(os.environ, NDG_NOTIFY="0")
    r = subprocess.run([sys.executable, HOOK], input=payload,
                       capture_output=True, text=True, env=env)
    out = (r.stdout or "").strip()
    if not out:
        return "proceed"
    try:
        return json.loads(out)["hookSpecificOutput"]["permissionDecision"]
    except Exception:
        return "proceed"


# В bypassPermissions поднимаем y/n ТОЛЬКО на CRITICAL (необратимо / бьёт за
# пределы рабочей копии).
BYPASS_CRITICAL = [
    ("rm -rf абс. путь", "rm -rf /var/data"),
    ("rm -rf ~", "rm -rf ~/Documents"),
    ("rm -r не-регенер.", "rm -r src"),
    ("rm -rf glob", "rm -rf *"),
    ("rm -rf .", "rm -rf ."),
    ("shred", "shred -u key"),
    ("srm", "srm secret"),
    ("dropdb", "dropdb mydb"),
    ("git reset --hard", "git reset --hard origin/main"),
    ("git clean -fd", "git clean -fd"),
    ("git push --force", "git push --force origin main"),
    ("git branch -D", "git branch -D feature"),
    ("docker volume rm", "docker volume rm data"),
    ("docker system prune", "docker system prune -a"),
    ("compose down -v", "docker compose down -v"),
    ("psql DELETE FROM", 'psql -c "DELETE FROM users"'),
    ("sqlite DROP TABLE", 'sqlite3 db "DROP TABLE t"'),
    ("find -delete", "find . -name '*.tmp' -delete"),
    ("find -exec rm", "find . -exec rm {} ;"),
    ("git -C reset --hard", "git -C /repo reset --hard"),
    ("bash -c rm -rf abs", 'bash -c "rm -rf /etc/x"'),
]

# В bypassPermissions проходят молча, но в default — спрашивают (ORDINARY).
BYPASS_ORDINARY = [
    ("rm file", "rm file.txt"),
    ("rm -f files", "rm -f a.log b.log"),
    ("rm -rf ./build", "rm -rf ./build"),
    ("rm -rf node_modules", "rm -rf node_modules"),
    ("rm -rf dist/", "rm -rf dist/"),
    ("rmdir", "rmdir olddir"),
    ("unlink", "unlink /tmp/link"),
    ("truncate", "truncate -s 0 x.log"),
    ("git rm", "git rm --cached f"),
    ("docker rm", "docker rm -f c1"),
    ("docker rmi", "docker rmi img"),
    ("docker image rm", "docker image rm img"),
]


class TestConfirmDestructive(unittest.TestCase):
    def test_hook_exists(self):
        self.assertTrue(os.path.exists(HOOK), f"hook not found: {HOOK}")

    def test_destructive_asks(self):
        for desc, cmd in ASK_CASES:
            with self.subTest(case=desc, cmd=cmd):
                self.assertEqual(decision(cmd), "ask", f"ожидали ask: {cmd}")

    def test_safe_proceeds(self):
        for desc, cmd in PROCEED_CASES:
            with self.subTest(case=desc, cmd=cmd):
                self.assertEqual(decision(cmd), "proceed", f"не должно спрашивать: {cmd}")

    def test_empty_command_proceeds(self):
        self.assertEqual(decision(""), "proceed")

    def test_bypass_critical_still_asks(self):
        for desc, cmd in BYPASS_CRITICAL:
            with self.subTest(case=desc, cmd=cmd):
                self.assertEqual(decision(cmd, "bypassPermissions"), "ask",
                                 f"CRITICAL должен спрашивать даже в bypass: {cmd}")

    def test_bypass_ordinary_proceeds_but_asks_default(self):
        for desc, cmd in BYPASS_ORDINARY:
            with self.subTest(case=desc, cmd=cmd):
                self.assertEqual(decision(cmd, "bypassPermissions"), "proceed",
                                 f"ORDINARY должен молча проходить в bypass: {cmd}")
                self.assertEqual(decision(cmd, "default"), "ask",
                                 f"ORDINARY должен спрашивать в default: {cmd}")

    def test_manifests_valid_json(self):
        for rel in (".claude-plugin/marketplace.json",
                    "destructive-guard/.claude-plugin/plugin.json",
                    "destructive-guard/hooks/hooks.json"):
            with self.subTest(file=rel):
                with open(os.path.join(ROOT, rel)) as f:
                    json.load(f)

    def test_marketplace_source_points_to_plugin(self):
        with open(os.path.join(ROOT, ".claude-plugin", "marketplace.json")) as f:
            mp = json.load(f)
        src = mp["plugins"][0]["source"]
        self.assertTrue(src.startswith("./"), f"source must start with ./ : {src}")
        self.assertTrue(
            os.path.exists(os.path.join(ROOT, src, ".claude-plugin", "plugin.json")),
            f"plugin.json not found at source {src}",
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
