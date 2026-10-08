"""Runs test agents with `claude -p` (Claude subscription, no API key) against the real HubSpot MCP server via the proxy.

  uv run python -m bench.run --questions g4-02 --arms S,S-expert,S-code,Q,Q-expert,Q-code --repeats 1
  uv run python -m bench.run --all --repeats 3                     # every question x arm x repeat, resumable

Needs the daemon running (uv run python -m bench.daemon). One run at a time, so timings don't compete.
Per run: private/runs/<run>/transcript.jsonl (stream-json), result.json, calls.jsonl (written by the daemon).
"""
import argparse, hashlib, json, os, random, shutil, subprocess, tarfile, time
from pathlib import Path

from bench.arms import ARMS

ROOT = Path(__file__).resolve().parent.parent
RUNS = ROOT / "private" / "runs"
# Outside every other temp folder of this session; one folder per run, archived and deleted after the run.
WORK = Path("/private/tmp/hsb-work")
PROMPTS = ROOT / "bench" / "prompts"
PY = ROOT / ".venv" / "bin" / "python"
TIMEOUT = 1200  # 20 minutes per run, all arms (a full scan in code needs at most ~5 min for these questions)
MODELS = {"opus": "claude-opus-5-5", "sonnet": "claude-sonnet-5-5"}
DENY_READ = ["~/.config", "~/.ssh", "~/Projects", "~/.claude", "~/.codex", "~/Documents", "~/Desktop", "~/Downloads", "~/.aws", "~/.netrc",
             "~/ai-posting", "/private/tmp/claude-501"]
PROVENANCE = ["bench/prompts/system.md", "bench/prompts/playbook-search.md", "bench/prompts/playbook-hubsql.md", "bench/prompts/code.md",
              "docs/questions.json", "bench/arms.py", "bench/stdio_proxy.py", "bench/hubspot_helper.py", "bench/daemon.py", "results/mcp-tools.json"]


def provenance():
    return {f: hashlib.sha256((ROOT / f).read_bytes()).hexdigest()[:16] for f in PROVENANCE}


def preflight():
    """Each arm's real tool list (via the stdio proxy) must equal its allowlist, with HubSpot's definitions unchanged."""
    defs = {t["name"]: t for t in json.loads((ROOT / "results" / "mcp-tools.json").read_text())}
    report = {}
    for arm in ARMS:
        msgs = [{"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"protocolVersion": "2025-06-18", "capabilities": {}, "clientInfo": {"name": "preflight", "version": "1"}}},
                {"jsonrpc": "2.0", "id": 2, "method": "tools/list"}]
        p = subprocess.run([str(PY), str(ROOT / "bench" / "stdio_proxy.py")], input="\n".join(json.dumps(m) for m in msgs) + "\n",
                           capture_output=True, text=True, env={**os.environ, "BENCH_RUN": "preflight", "BENCH_ARM": arm}, timeout=60)
        tools = [json.loads(l) for l in p.stdout.splitlines() if l.strip()][1]["result"]["tools"]
        names = [t["name"] for t in tools]
        assert names == ARMS[arm]["tools"], (arm, names)
        for t in tools:
            assert t["description"] == defs[t["name"]]["description"] and t["inputSchema"] == defs[t["name"]]["input_schema"], (arm, t["name"])
        report[arm] = names
    (ROOT / "private" / "preflight.json").write_text(json.dumps({"checked": time.time(), "provenance": provenance(), "arms": report}, indent=1))
    return report


def system_prompt(arm):
    s = (PROMPTS / "system.md").read_text().strip()
    if ARMS[arm]["playbook"]:
        s += "\n" + (PROMPTS / f"playbook-{ARMS[arm]['playbook']}.md").read_text().rstrip()
    if ARMS[arm]["code"]:
        s += "\n" + (PROMPTS / "code.md").read_text().rstrip()
    return s


def user_message(q):
    return f"{q['question']}\n\nExact definition that will be used to check your answer:\n{q['definition']}"


def run_one(q, arm, model, rep):
    run = f"{q['id']}__{arm}__{model}__r{rep}"
    out = RUNS / run
    if (out / "result.json").exists():
        return None
    if out.exists():
        shutil.rmtree(out)  # an interrupted run starts over
    out.mkdir(parents=True)
    shutil.rmtree(WORK, ignore_errors=True)  # no other run's files exist while this one runs
    wd = WORK / run
    (wd / "tmp").mkdir(parents=True)
    mcp = {"mcpServers": {"hubspot": {"type": "stdio", "command": str(PY), "args": [str(ROOT / "bench" / "stdio_proxy.py")],
                                      "env": {"BENCH_RUN": run, "BENCH_ARM": arm}}}}
    (out / "mcp.json").write_text(json.dumps(mcp))
    settings = {"permissions": {"defaultMode": "dontAsk", "allow": ["mcp__hubspot__*"]}}
    tools = ""
    if ARMS[arm]["code"]:
        shutil.copy(ROOT / "bench" / "hubspot_helper.py", wd / "hubspot.py")
        tools = "Bash"
        settings = {"sandbox": {"enabled": True, "failIfUnavailable": True, "autoAllowBashIfSandboxed": True, "allowUnsandboxedCommands": False,
                                "filesystem": {"denyRead": DENY_READ, "allowWrite": [str(wd)]},
                                "network": {"allowedDomains": ["127.0.0.1:8799", "localhost:8799"], "allowLocalBinding": False}},
                    "permissions": {"defaultMode": "dontAsk", "allow": ["mcp__hubspot__*", "Bash"]},
                    "env": {"BASH_DEFAULT_TIMEOUT_MS": str(TIMEOUT * 1000), "BASH_MAX_TIMEOUT_MS": str(TIMEOUT * 1000)}}
    (out / "settings.json").write_text(json.dumps(settings))
    cmd = ["claude", "-p", "--model", MODELS[model], "--system-prompt", system_prompt(arm), "--tools", tools,
           "--strict-mcp-config", "--mcp-config", str(out / "mcp.json"), "--setting-sources", "",
           "--settings", str(out / "settings.json"), "--allowedTools", "mcp__hubspot__*", *(["Bash"] if tools else []),
           "--output-format", "stream-json", "--verbose", user_message(q)]
    env = {k: v for k, v in os.environ.items() if k not in ("ANTHROPIC_API_KEY", "ANTHROPIC_AUTH_TOKEN")}
    env.update({"BENCH_RUN": run, "BENCH_ARM": arm, "TMPDIR": str(wd / "tmp"),
                # Claude Code stops a single Bash command after 10 minutes by default; a full scan in code needs longer.
                "BASH_DEFAULT_TIMEOUT_MS": str(TIMEOUT * 1000), "BASH_MAX_TIMEOUT_MS": str(TIMEOUT * 1000)})
    t0 = time.time()
    timed_out = False
    with open(out / "transcript.jsonl", "w") as f:
        p = subprocess.Popen(cmd, cwd=wd, env=env, stdin=subprocess.DEVNULL, stdout=f, stderr=subprocess.PIPE, text=True)
        try:
            _, err = p.communicate(timeout=TIMEOUT)
        except subprocess.TimeoutExpired:
            p.kill()
            _, err = p.communicate()
            timed_out = True
    wall = round(time.time() - t0, 1)
    with tarfile.open(out / "workdir.tar.gz", "w:gz") as tar:  # the agent's scripts and files, kept as evidence
        tar.add(wd, arcname=run)
    shutil.rmtree(WORK, ignore_errors=True)
    final = None
    for line in (out / "transcript.jsonl").read_text().split("\n"):
        try:
            m = json.loads(line)
        except ValueError:
            continue
        if m.get("type") == "result":
            final = m
    res = {"run": run, "question": q["id"], "group": q["group"], "arm": arm, "model": MODELS[model], "repeat": rep,
           "started": t0, "wall_seconds": wall, "timed_out": timed_out, "exit_code": p.returncode, "stderr": (err or "")[-2000:],
           "answer": (final or {}).get("result"), "num_turns": (final or {}).get("num_turns"),
           "duration_ms": (final or {}).get("duration_ms"), "cost_usd_equivalent": (final or {}).get("total_cost_usd"),
           "usage": (final or {}).get("usage"), "terminal_reason": (final or {}).get("terminal_reason"),
           "is_error": (final or {}).get("is_error"), "provenance": provenance()}
    (out / "result.json").write_text(json.dumps(res, indent=1, ensure_ascii=False))
    with open(RUNS / "manifest.jsonl", "a") as f:
        f.write(json.dumps({k: res[k] for k in ("run", "arm", "model", "question", "repeat", "wall_seconds", "timed_out", "cost_usd_equivalent")}) + "\n")
    return res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--questions", default="")
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--arms", default=",".join(ARMS))
    ap.add_argument("--model", default="opus", choices=list(MODELS))
    ap.add_argument("--repeats", type=int, default=1)
    a = ap.parse_args()
    qs = json.loads((ROOT / "docs" / "questions.json").read_text())
    if not a.all:
        qs = [q for q in qs if q["id"] in a.questions.split(",")]
    arms = a.arms.split(",")
    RUNS.mkdir(parents=True, exist_ok=True)
    print("preflight:", preflight(), flush=True)
    for rep in range(1, a.repeats + 1):
        for q in qs:
            order = arms[:]
            random.Random(f"{q['id']}-{rep}-{a.model}").shuffle(order)  # recorded: the seed is the block name
            for arm in order:
                res = run_one(q, arm, a.model, rep)
                if res:
                    print(f"{res['run']}: {res['wall_seconds']} s, turns {res['num_turns']}, ${res['cost_usd_equivalent'] or 0:.2f} eq, "
                          f"timeout={res['timed_out']} | {(res['answer'] or '')[:160]!r}", flush=True)


if __name__ == "__main__":
    main()
