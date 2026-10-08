"""Read-only HubSQL queries on the Sellestial portal (token from ~/.config/jevbench/env). Results saved next to it."""
import json, sys, time
from pathlib import Path
import httpx

env = dict(l.split("=", 1) for l in Path.home().joinpath(".config/jevbench/env").read_text().splitlines()
           if "=" in l and not l.startswith("#"))
TOKEN = env["HUBSPOT_TOKEN"].strip().strip('"').strip("'")
URL = "https://api.hubapi.com/analytics/hubsql/2027-03-beta/query"
OUT = Path(__file__).with_name("results.json")

def q(sql, page_size=100):
    t = time.monotonic()
    r = httpx.post(URL, headers={"Authorization": f"Bearer {TOKEN}"}, json={"query": sql, "pageSize": page_size}, timeout=60)
    time.sleep(1.1)  # 1 request per second
    body = r.json() if r.headers.get("content-type", "").startswith("application/json") else {"raw": r.text[:300]}
    return {"sql": sql, "status": r.status_code, "seconds": round(time.monotonic() - t, 2), "body": body}

QUERIES = {
    "contacts_total": "SELECT COUNT(*) FROM OBJECT.CONTACT",
    "contacts_no_company": "SELECT COUNT(*) FROM OBJECT.CONTACT WHERE associatedcompanyid IS NULL",
    "companies_total": "SELECT COUNT(*) FROM OBJECT.COMPANY",
    "companies_no_domain": "SELECT COUNT(*) FROM OBJECT.COMPANY WHERE domain IS NULL",
    "shared_domains_top": "SELECT domain, COUNT(*) AS n FROM OBJECT.COMPANY WHERE domain IS NOT NULL GROUP BY domain ORDER BY n DESC LIMIT 500",
    "contacts_by_lifecycle": "SELECT lifecyclestage, COUNT(*) AS n FROM OBJECT.CONTACT GROUP BY lifecyclestage ORDER BY n DESC LIMIT 50",
    "contacts_no_owner": "SELECT COUNT(*) FROM OBJECT.CONTACT WHERE hubspot_owner_id IS NULL",
    "contacts_by_lifecycle_owner": "SELECT lifecyclestage, hubspot_owner_id, COUNT(*) AS n FROM OBJECT.CONTACT GROUP BY lifecyclestage, hubspot_owner_id ORDER BY n DESC LIMIT 100",
    "deals_total": "SELECT COUNT(*) FROM OBJECT.DEAL",
}
results = {}
for name, sql in QUERIES.items():
    results[name] = q(sql)
    b = results[name]["body"]
    short = json.dumps(b.get("results", b))[:220] if isinstance(b, dict) else str(b)[:220]
    print(f"{name:28} {results[name]['status']} {results[name]['seconds']}s total={b.get('total') if isinstance(b, dict) else ''} {short}", flush=True)
OUT.write_text(json.dumps(results, indent=1))
