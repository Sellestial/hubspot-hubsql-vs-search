"""Reference answers for docs/questions.json, computed exactly from full exports (bench/export.py). No AI.

  uv run python -m bench.truth                     # newest exports -> private/truth-<contacts export stamp>.json
  uv run python -m bench.truth <contacts.jsonl.gz> <companies.jsonl.gz>
"""
import os, gzip, json, re, sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parent.parent
EXPORT = ROOT / "private" / "export"
ENV = {k.strip(): v.strip().strip('"').strip("'") for k, v in (l.split("=", 1) for l in
       Path(os.environ.get("HUBSQL_BENCH_ENV", Path.home() / ".config/hubsql-bench/env")).read_text().splitlines() if "=" in l and not l.startswith("#"))}

CONTACT_FIELDS = ["jobtitle", "hs_latest_source", "hs_latest_source_timestamp", "lifecyclestage", "hs_marketable_status", "industry",
                  "hs_analytics_source", "hs_analytics_num_visits"]
COMPANY_FIELDS = ["founded_year", "sellestial_icp", "hq_country_linkedin", "createdate", "hs_country_code", "state",
                  "builtwith_contains_hubspot", "sellestial_seo_score"]


def newest(obj, fields):
    for p in sorted(EXPORT.glob(f"{obj}-*.jsonl.gz"), reverse=True):
        with gzip.open(p, "rt") as f:
            first = json.loads(f.readline())
        if all(k in first for k in fields):
            return p
    raise SystemExit(f"no {obj} export with all fields; run: uv run python -m bench.export {obj} {','.join(fields)}")


def rows(p):
    with gzip.open(p, "rt") as f:
        for line in f:
            yield json.loads(line)


def labels(obj, prop):
    r = httpx.get(f"https://api.hubapi.com/crm/v3/properties/{obj}/{prop}", headers={"Authorization": f"Bearer {ENV['HUBSPOT_TOKEN']}"}, timeout=60)
    return {o["value"]: o["label"] for o in r.json().get("options", [])}


def ts(v):
    return datetime.fromisoformat(v.replace("Z", "+00:00")) if v else None


def num(v):
    try:
        return float(v) if v not in (None, "") else None
    except ValueError:
        return None


def ranked(counter, label=lambda k: k):
    """All values, ordered by count desc, then label asc (case-insensitive)."""
    return sorted(counter.items(), key=lambda kv: (-kv[1], str(label(kv[0])).lower()))


def top(counter, n, label=lambda k: k):
    items = ranked(counter, label)
    if len(items) <= n:
        return {"top": items, "tied_at_last": []}
    cut = items[n - 1][1]
    return {"top": items[:n], "tied_at_last": [kv for kv in items[n:] if kv[1] == cut], "next": items[n]}


def compute(pc, pk):
    U = lambda y, m, d: datetime(y, m, d, tzinfo=timezone.utc)  # noqa: E731
    life_lab, latest_lab = labels("contacts", "lifecyclestage"), labels("contacts", "hs_latest_source")
    revops, latest_sep, life_mkt, cind, paid_visits, paid_n, n_contacts = 0, Counter(), Counter(), Counter(), 0.0, 0, 0
    for r in rows(pc):
        n_contacts += 1
        jt = (r["jobtitle"] or "").lower()
        if "revops" in jt or "revenue operations" in jt:
            revops += 1
        t = ts(r["hs_latest_source_timestamp"])
        if t and r["hs_latest_source"] and U(2026, 9, 1) <= t < U(2026, 10, 1):
            latest_sep[r["hs_latest_source"]] += 1
        if r["lifecyclestage"] and r["hs_marketable_status"] in ("true", "false"):
            life_mkt[(r["lifecyclestage"], "marketing" if r["hs_marketable_status"] == "true" else "non-marketing")] += 1
        v = (r["industry"] or "").strip().lower()
        if v:
            cind[v] += 1
        if r["hs_analytics_source"] == "PAID_SOCIAL" and num(r["hs_analytics_num_visits"]) is not None:
            paid_visits += num(r["hs_analytics_num_visits"])
            paid_n += 1
    founded, icp_hq, quarters, us_state, seo, n_companies = 0, Counter(), Counter(), Counter(), [], 0
    for r in rows(pk):
        n_companies += 1
        fy = (r["founded_year"] or "").strip()
        if re.fullmatch(r"\d{4}", fy) and int(fy) >= 2020:
            founded += 1
        if r["sellestial_icp"] == "true" and r["hq_country_linkedin"]:
            icp_hq[r["hq_country_linkedin"]] += 1
        c = ts(r["createdate"])
        if c and U(2025, 1, 1) <= c < U(2026, 1, 1):
            quarters[f"2025-Q{(c.month - 1) // 3 + 1}"] += 1
        if (r["hs_country_code"] or "").strip().lower() == "us":
            s = (r["state"] or "").strip().lower()
            if s:
                us_state[s] += 1
        if r["builtwith_contains_hubspot"] == "true" and num(r["sellestial_seo_score"]) is not None:
            seo.append(num(r["sellestial_seo_score"]))
    stages = sorted({s for s, _ in life_mkt})
    return {
        "counts": {"contacts": n_contacts, "companies": n_companies},
        "answers": {
            "g1-05": {"value": revops},
            "g1-09": {"value": founded},
            "g2-04": top(icp_hq, 10),
            "g2-10": {"top": ranked(latest_sep, lambda k: latest_lab.get(k, k)), "tied_at_last": [], "full_list": True,
                      "labels": {k: latest_lab.get(k, k) for k in latest_sep}},
            "g3-02": {"rows": {q: quarters.get(q, 0) for q in ("2025-Q1", "2025-Q2", "2025-Q3", "2025-Q4")}},
            "g3-04": {"matrix": {s: {"marketing": life_mkt.get((s, "marketing"), 0), "non-marketing": life_mkt.get((s, "non-marketing"), 0)} for s in stages},
                      "labels": {s: life_lab.get(s, s) for s in stages}},
            "g4-09": {**top(us_state, 10), "distinct": len(us_state), "with_value": sum(us_state.values())},
            "g4-10": {**top(cind, 10), "distinct": len(cind), "with_value": sum(cind.values())},
            "g5-09": {"value": paid_visits, "n": paid_n},
            "g5-10": {"value": sum(seo) / len(seo), "n": len(seo)},
        },
    }


def main():
    pc, pk = (Path(sys.argv[1]), Path(sys.argv[2])) if len(sys.argv) == 3 else (newest("contacts", CONTACT_FIELDS), newest("companies", COMPANY_FIELDS))
    out = {"exports": [pc.name, pk.name], **compute(pc, pk)}
    path = ROOT / "private" / f"truth-{pc.name.split('-', 1)[1].split('.')[0]}.json"
    path.write_text(json.dumps(out, indent=1, ensure_ascii=False))
    print(path.name)
    print(json.dumps(out, indent=1, ensure_ascii=False)[:5000])


if __name__ == "__main__":
    main()
