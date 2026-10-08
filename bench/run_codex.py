"""Runs the test agents with the Codex CLI (GPT gpt-6.1-sol, reasoning effort xhigh; ChatGPT login, no API key).

  uv run python -m bench.run_codex --questions g3-02 --repeats 1
  uv run python -m bench.run_codex --all --repeats 3              # every question x arm x repeat, resumable

Same questions, prompts (as developer instructions), arms, MCP proxy and logging as bench/run.py. Differences:
- Codex's own config, plugins, memories and MCP servers are not loaded (--ignore-user-config, --ephemeral).
- No-code arms get no shell (features shell_tool and unified_exec off); code arms get a shell and the helper.
- Every run is wrapped in a macOS sandbox (bench/agent.sb, copied to /private/tmp/hsb-proxy) that blocks reads of
  ~/.config, ~/.ssh, ~/Projects and other private folders and blocks writes in the home folder (except ~/.codex),
  because Codex's own sandbox does not restrict reads. Codex's sandbox is therefore bypassed inside it.
- The MCP proxy runs from a copy in /private/tmp/hsb-proxy with the system Python (stdlib only); the copy is checked
  byte for byte against the repository before every batch.
"""
import argparse, filecmp, json, os, random, shutil, subprocess, tarfile, time
from collections import Counter
from pathlib import Path

from bench.arms import ARMS
from bench.run import RUNS, ROOT, WORK, preflight, provenance, system_prompt, user_message

MODEL, EFFORT, TAG = "gpt-6.1-sol", "xhigh", "gpt61sol"
TIMEOUT = 1200  # 20 minutes per run, all arms
PROXY = Path("/private/tmp/hsb-proxy")
PROXY_FILES = {"bench/__init__.py": "bench/__init__.py", "bench/arms.py": "bench/arms.py", "bench/stdio_proxy.py": "bench/stdio_proxy.py",
               "results/mcp-tools.json": "results/mcp-tools.json", "bench/agent.sb": "agent.sb"}
OFF_ALWAYS = ["apps", "plugins", "browser_use", "browser_use_external", "computer_use", "image_generation", "multi_agent", "goals",
              "tool_suggest", "view_image", "memories"]
OFF_NO_CODE = ["shell_tool", "unified_exec"]


def sync_proxy():
    for src, dst in PROXY_FILES.items():
        (PROXY / dst).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(ROOT / src, PROXY / dst)
        assert filecmp.cmp(ROOT / src, PROXY / dst, shallow=False), src


def run_one(q, arm, rep):
    run = f"{q['id']}__{arm}__{TAG}__r{rep}"
    out = RUNS / run
    if (out / "result.json").exists():
        return None
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)
    shutil.rmtree(WORK, ignore_errors=True)  # no other run's files exist while this one runs
    wd = WORK / run
    (wd / "tmp").mkdir(parents=True)
    if ARMS[arm]["code"]:
        shutil.copy(ROOT / "bench" / "hubspot_helper.py", wd / "hubspot.py")
    off = OFF_ALWAYS + ([] if ARMS[arm]["code"] else OFF_NO_CODE)
    cmd = ["sandbox-exec", "-D", f"HOME={Path.home()}", "-f", str(PROXY / "agent.sb"), "codex", "exec", "--ignore-user-config", "--ephemeral", "--skip-git-repo-check",
           "--dangerously-bypass-approvals-and-sandbox", "-m", MODEL, "-c", f'model_reasoning_effort="{EFFORT}"', "-c", 'web_search="disabled"',
           "-c", "developer_instructions=" + json.dumps(system_prompt(arm)),
           "-c", 'mcp_servers.hubspot.command="/usr/bin/python3"', "-c", f'mcp_servers.hubspot.args=["{PROXY}/bench/stdio_proxy.py"]',
           "-c", f'mcp_servers.hubspot.env={{BENCH_RUN="{run}",BENCH_ARM="{arm}"}}', "-c", "mcp_servers.hubspot.tool_timeout_sec=600",
           *[a for f in off for a in ("--disable", f)], "--json", "-o", str(wd / "last_message.txt"), user_message(q)]
    (out / "command.json").write_text(json.dumps(cmd, indent=1, ensure_ascii=False))
    env = {k: v for k, v in os.environ.items() if k not in ("ANTHROPIC_API_KEY", "ANTHROPIC_AUTH_TOKEN", "OPENAI_API_KEY")}
    env.update({"BENCH_RUN": run, "BENCH_ARM": arm, "TMPDIR": str(wd / "tmp")})
    t0 = time.time()
    timed_out = False
    # Output through pipes: Node aborts at start when stdout points into a folder the sandbox blocks (~/Projects).
    p = subprocess.Popen(cmd, cwd=wd, env=env, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    try:
        stdout, err = p.communicate(timeout=TIMEOUT)
    except subprocess.TimeoutExpired:
        p.kill()
        stdout, err = p.communicate()
        timed_out = True
    (out / "transcript.jsonl").write_text(stdout or "")
    wall = round(time.time() - t0, 1)
    if (wd / "last_message.txt").exists():
        shutil.copy(wd / "last_message.txt", out / "last_message.txt")
    with tarfile.open(out / "workdir.tar.gz", "w:gz") as tar:  # the agent's scripts and files, kept as evidence
        tar.add(wd, arcname=run)
    shutil.rmtree(WORK, ignore_errors=True)
    usage, answer, turns, items = {}, None, 0, Counter()
    for line in (out / "transcript.jsonl").read_text().split("\n"):
        try:
            m = json.loads(line)
        except ValueError:
            continue
        if m.get("type") == "turn.completed":
            turns += 1
            for k, v in (m.get("usage") or {}).items():
                usage[k] = usage.get(k, 0) + (v or 0)
        if m.get("type") == "item.completed":
            items[m["item"].get("type")] += 1
            if m["item"].get("type") == "agent_message":
                answer = m["item"].get("text")
    last = out / "last_message.txt"
    if last.exists() and last.read_text().strip():
        answer = last.read_text()
    res = {"run": run, "question": q["id"], "group": q["group"], "arm": arm, "model": f"{MODEL} ({EFFORT})", "repeat": rep,
           "started": t0, "wall_seconds": wall, "timed_out": timed_out, "exit_code": p.returncode, "stderr": (err or "")[-2000:],
           "answer": answer if not timed_out else None, "num_turns": turns, "items": dict(items), "usage": usage,
           "cost_usd_equivalent": None, "provenance": provenance()}
    (out / "result.json").write_text(json.dumps(res, indent=1, ensure_ascii=False))
    with open(RUNS / "manifest.jsonl", "a") as f:
        f.write(json.dumps({k: res[k] for k in ("run", "arm", "model", "question", "repeat", "wall_seconds", "timed_out")}) + "\n")
    return res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--questions", default="")
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--arms", default=",".join(ARMS))
    ap.add_argument("--repeats", type=int, default=1)
    a = ap.parse_args()
    qs = json.loads((ROOT / "docs" / "questions.json").read_text())
    if not a.all:
        qs = [q for q in qs if q["id"] in a.questions.split(",")]
    arms = a.arms.split(",")
    RUNS.mkdir(parents=True, exist_ok=True)
    sync_proxy()
    print("preflight:", preflight(), flush=True)
    for rep in range(1, a.repeats + 1):
        for q in qs:
            order = arms[:]
            random.Random(f"{q['id']}-{rep}-{TAG}").shuffle(order)  # recorded: the seed is the block name
            for arm in order:
                res = run_one(q, arm, rep)
                if res:
                    print(f"{res['run']}: {res['wall_seconds']} s, turns {res['num_turns']}, items {res['items']}, timeout={res['timed_out']} "
                          f"| {(res['answer'] or '')[:150]!r}", flush=True)


if __name__ == "__main__":
    main()
