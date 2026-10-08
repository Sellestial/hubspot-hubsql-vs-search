"""Reference export: every record of an object with the given fields, read with the CRM search API (no AI).

Pages through the whole object in record-ID order, restarting the search from the last ID before the 10,000-result cap,
so nothing is skipped. Writes private/export/<object>-<UTC timestamp>.jsonl.gz and prints the record count.

  uv run python -m bench.export contacts jobtitle,createdate,...
"""
import os, gzip, json, sys, time
from datetime import datetime, timezone
from pathlib import Path

import httpx

ENV = {k.strip(): v.strip().strip('"').strip("'") for k, v in (l.split("=", 1) for l in
       Path(os.environ.get("HUBSQL_BENCH_ENV", Path.home() / ".config/hubsql-bench/env")).read_text().splitlines() if "=" in l and not l.startswith("#"))}
H = {"Authorization": f"Bearer {ENV['HUBSPOT_TOKEN']}"}
OUT = Path(__file__).resolve().parent.parent / "private" / "export"


def search(obj, body, client):
    for i in range(8):
        r = client.post(f"https://api.hubapi.com/crm/v3/objects/{obj}/search", headers=H, json=body, timeout=60)
        if r.status_code in (429, 502, 503, 504):
            time.sleep(1 + 2 * i)
            continue
        r.raise_for_status()
        return r.json()
    raise RuntimeError(f"search failed: {r.status_code} {r.text[:200]}")


def export(obj, fields):
    OUT.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    path = OUT / f"{obj}-{stamp}.jsonl.gz"
    n, last_id, t0 = 0, 0, time.time()
    with httpx.Client() as client, gzip.open(path, "wt") as f:
        while True:
            after, got_any = None, False
            while True:  # one search window: ids > last_id, at most 10,000 results
                body = {"limit": 200, "properties": fields, "sorts": [{"propertyName": "hs_object_id", "direction": "ASCENDING"}],
                        "filterGroups": [{"filters": [{"propertyName": "hs_object_id", "operator": "GT", "value": str(last_id)}]}]}
                if after:
                    body["after"] = after
                b = search(obj, body, client)
                time.sleep(0.2)  # 5 requests per second
                for rec in b["results"]:
                    f.write(json.dumps({"id": int(rec["id"]), **{k: rec["properties"].get(k) for k in fields}}) + "\n")
                    n += 1
                    got_any = True
                    window_last = int(rec["id"])
                after = ((b.get("paging") or {}).get("next") or {}).get("after")
                if not after or int(after) >= 9800:
                    break
            if not got_any:
                break
            last_id = window_last
            print(f"{obj}: {n:,} records, last id {last_id}, {time.time() - t0:.0f} s", flush=True)
    print(f"done: {n:,} {obj} -> {path.name}", flush=True)
    return path


if __name__ == "__main__":
    export(sys.argv[1], sys.argv[2].split(","))
