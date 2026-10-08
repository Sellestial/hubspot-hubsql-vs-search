"""Property profile for contacts and companies: name, label, type, options, and how many records have a value.
No record data. Uses the private app token (REST, read-only). Output: private/props-profile.json"""
import os, json, time
from pathlib import Path
import httpx

ENV = {k.strip(): v.strip().strip('"').strip("'") for k, v in (l.split("=", 1) for l in
       Path(os.environ.get("HUBSQL_BENCH_ENV", Path.home() / ".config/hubsql-bench/env")).read_text().splitlines() if "=" in l and not l.startswith("#"))}
H = {"Authorization": f"Bearer {ENV['HUBSPOT_TOKEN']}"}
OUT = Path(__file__).resolve().parent.parent / "private" / "props-profile.json"

def get(url, **kw):
    for i in range(6):
        r = httpx.request(kw.pop("method", "GET") if False else ("POST" if "json" in kw else "GET"), url, headers=H, timeout=60, **kw)
        if r.status_code == 429:
            time.sleep(2 + 2 * i); continue
        r.raise_for_status(); return r.json()
    raise RuntimeError(url)

def main():
    prof = {}
    for obj in ("contacts", "companies"):
        props = get(f"https://api.hubapi.com/crm/v3/properties/{obj}")["results"]
        total = get(f"https://api.hubapi.com/crm/v3/objects/{obj}/search", json={"limit": 1})["total"]
        rows = []
        for p in props:
            if p.get("hidden"):
                continue
            n = get(f"https://api.hubapi.com/crm/v3/objects/{obj}/search", json={"limit": 1, "filterGroups": [{"filters": [{"propertyName": p["name"], "operator": "HAS_PROPERTY"}]}]}).get("total")
            time.sleep(0.22)
            rows.append({"name": p["name"], "label": p.get("label"), "type": p.get("type"), "fieldType": p.get("fieldType"),
                         "options": len(p.get("options") or []), "calculated": bool(p.get("calculated")),
                         "hubspotDefined": bool(p.get("hubspotDefined")), "group": p.get("groupName"), "filled": n})
        prof[obj] = {"total": total, "properties": sorted(rows, key=lambda r: -(r["filled"] or 0))}
        print(obj, total, "records,", len(rows), "visible properties", flush=True)
    OUT.write_text(json.dumps(prof, indent=1))


if __name__ == "__main__":
    main()
