"""MCP stdio server that Claude Code launches for one test run. Stdlib only.

Lists the arm's tools exactly as HubSpot's remote MCP server defines them (results/mcp-tools.json) and forwards
each call, unchanged, to the local daemon. Env: BENCH_RUN, BENCH_ARM, BENCH_DAEMON (default http://127.0.0.1:8799).
"""
import json, os, sys, urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from bench.arms import ARMS  # noqa: E402

RUN, ARM = os.environ["BENCH_RUN"], os.environ["BENCH_ARM"]
DAEMON = os.environ.get("BENCH_DAEMON", "http://127.0.0.1:8799")
ALL = {t["name"]: t for t in json.loads((ROOT / "results" / "mcp-tools.json").read_text())}
TOOLS = [{"name": n, "title": ALL[n].get("title"), "description": ALL[n].get("description", ""),
          "inputSchema": ALL[n]["input_schema"], **({"annotations": ALL[n]["annotations"]} if ALL[n].get("annotations") else {})}
         for n in ARMS[ARM]["tools"]]
TOOLS = [{k: v for k, v in t.items() if v is not None} for t in TOOLS]


def forward(name, args):
    req = urllib.request.Request(DAEMON, data=json.dumps({"run": RUN, "arm": ARM, "tool": name, "args": args, "via": "direct"}).encode(),
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=620) as r:
        res = json.loads(r.read())
    return {k: res[k] for k in ("content", "structuredContent", "isError") if k in res}


def reply(id_, result=None, error=None):
    msg = {"jsonrpc": "2.0", "id": id_, **({"error": error} if error else {"result": result})}
    sys.stdout.write(json.dumps(msg, ensure_ascii=False) + "\n")
    sys.stdout.flush()


for line in sys.stdin:
    if not line.strip():
        continue
    msg = json.loads(line)
    method, id_ = msg.get("method"), msg.get("id")
    if id_ is None:
        continue  # notifications
    if method == "initialize":
        reply(id_, {"protocolVersion": msg["params"].get("protocolVersion", "2025-06-18"),
                    "capabilities": {"tools": {"listChanged": False}},
                    "serverInfo": {"name": "hubspot", "version": "proxy-1"}})
    elif method == "tools/list":
        reply(id_, {"tools": TOOLS})
    elif method == "tools/call":
        try:
            reply(id_, forward(msg["params"]["name"], msg["params"].get("arguments") or {}))
        except Exception as exc:  # noqa: BLE001
            reply(id_, {"content": [{"type": "text", "text": f"proxy error: {exc!s:.300}"}], "isError": True})
    elif method == "ping":
        reply(id_, {})
    else:
        reply(id_, error={"code": -32601, "message": f"method not found: {method}"})
