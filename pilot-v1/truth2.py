import json, time
from pathlib import Path
import httpx
env = dict(l.split("=", 1) for l in Path.home().joinpath(".config/jevbench/env").read_text().splitlines() if "=" in l and not l.startswith("#"))
H = {"Authorization": f"Bearer {env['HUBSPOT_TOKEN'].strip().strip(chr(34)).strip(chr(39))}"}
def q(sql, size=100):
    r = httpx.post("https://api.hubapi.com/analytics/hubsql/2027-03-beta/query", headers=H, json={"query": sql, "pageSize": size}, timeout=60); time.sleep(1.1)
    assert r.status_code == 200, r.text; return r.json().get("results")
t = {"C1": q("SELECT jobtitle, COUNT(*) AS n FROM OBJECT.CONTACT WHERE jobtitle IS NOT NULL GROUP BY jobtitle ORDER BY n DESC LIMIT 10"),
     "C1_with_title": q("SELECT COUNT(*) FROM OBJECT.CONTACT WHERE jobtitle IS NOT NULL"),
     "C2": q("SELECT AVG(numberofemployees), COUNT(*) FROM OBJECT.COMPANY WHERE numberofemployees IS NOT NULL"),
     "C3": q("SELECT industry, COUNT(*) AS n FROM OBJECT.COMPANY WHERE industry IS NOT NULL GROUP BY industry ORDER BY n DESC LIMIT 10"),
     "C4": q("SELECT DATE_TRUNC(createdate, 'MONTH') AS month, hs_object_source_label, COUNT(*) AS n FROM OBJECT.CONTACT WHERE createdate >= '2026-01-01' GROUP BY month, hs_object_source_label ORDER BY month LIMIT 500"),
     "C5": q("SELECT COUNT(*) FROM OBJECT.COMPANY WHERE domain IS NULL")}
Path(__file__).with_name("truth2.json").write_text(json.dumps(t, indent=1))
print(json.dumps(t)[:1500])
