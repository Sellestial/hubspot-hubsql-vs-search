"""Follow-up check after the 360 runs: does an "equals" filter on company state match exactly?

Counts US companies per state three ways and writes results/check-equals.json:
  - the MCP server's search tool (search_crm_objects, state EQ <value>), through the local daemon
  - HubSQL through the MCP server (query_crm_data, state = '<value>'), through the local daemon
  - HubSpot's REST search API (crm/v3/objects/companies/search, state EQ <value>), with HUBSPOT_TOKEN
Read-only. Needs the daemon running (uv run python -m bench.daemon).

  uv run python -m bench.check_equals
"""
import json, os, time, urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ENV = {k: v for k, v in (l.split("=", 1) for l in
       Path(os.environ.get("HUBSQL_BENCH_ENV", Path.home() / ".config/hubsql-bench/env")).read_text().splitlines()
       if "=" in l and not l.startswith("#"))}
DAEMON = os.environ.get("BENCH_DAEMON", "http://127.0.0.1:8799")
STATES = ["Virginia", "West Virginia", "California"]


def post(url, body, headers):
    req = urllib.request.Request(url, data=json.dumps(body).encode(), headers={"Content-Type": "application/json", **headers})
    with urllib.request.urlopen(req, timeout=120) as r:
        return json.loads(r.read())


def mcp(arm, tool, args):
    res = post(DAEMON, {"run": "check-equals", "arm": arm, "tool": tool, "args": args, "via": "code"}, {})
    text = res["content"][0]["text"]
    return text if res.get("isError") else json.loads(text)


def filters(state):
    return [{"filters": [{"propertyName": "state", "operator": "EQ", "value": state},
                         {"propertyName": "hs_country_code", "operator": "EQ", "value": "US"}]}]


def main():
    out = {"checked_at": datetime.now(timezone.utc).isoformat(timespec="seconds"), "states": {}}
    for st in STATES:
        row = {}
        r = mcp("S-code", "search_crm_objects", {"objectType": "COMPANY", "limit": 1, "properties": ["state"], "filterGroups": filters(st)})
        row["mcp_search_tool"] = r["total"] if isinstance(r, dict) else f"error: {r[:120]}"
        r = mcp("Q-code", "query_crm_data", {"sql": f"SELECT COUNT(*) FROM company WHERE state = '{st}' AND hs_country_code = 'US'"})
        row["mcp_hubsql"] = r if isinstance(r, dict) else f"error: {r[:120]}"
        r = post("https://api.hubapi.com/crm/v3/objects/companies/search",
                 {"limit": 1, "properties": ["state"], "filterGroups": filters(st)},
                 {"Authorization": f"Bearer {ENV['HUBSPOT_TOKEN']}"})
        row["rest_search_api"] = r["total"]
        out["states"][st] = row
        print(st, row)
        time.sleep(1)
    (ROOT / "results" / "check-equals.json").write_text(json.dumps(out, indent=2) + "\n")


if __name__ == "__main__":
    main()
