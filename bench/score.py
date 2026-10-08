"""Scores every finished run against the reference answers.

Step 1 (extract): Codex (gpt-6.1-sol, no tools, fixed JSON schema) reads the question and the final answer, without knowing the
arm, and writes the claimed result into a fixed JSON shape (private/runs/<run>/extracted.json).
Step 2 (compare): plain code compares the extracted result with private/truth-*.json.

  uv run python -m bench.score            # extracts what is missing, then prints and saves private/scores.json
"""
import json, os, shutil, subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RUNS = ROOT / "private" / "runs"
QUESTIONS = {q["id"]: q for q in json.loads((ROOT / "docs" / "questions.json").read_text())}
SHAPES = {
    "value": '{"value": <number or null>, "says_uncertain": <true if the answer says the number is an estimate, approximate, incomplete or not verified>}',
    "ranking": '{"items": [{"name": "<value or option as written>", "count": <number or null>}, ...in the answer\'s order], "says_uncertain": <true/false as above>}',
    "quarters": '{"rows": {"2025-Q1": <number or null>, "2025-Q2": ..., "2025-Q3": ..., "2025-Q4": ...}, "says_uncertain": <true/false>}',
    "matrix": '{"rows": [{"stage": "<lifecycle stage as written>", "marketing": <number or null>, "non_marketing": <number or null>}, ...], "says_uncertain": <true/false>}',
}
KIND = {"g1-05": "value", "g1-09": "value", "g5-09": "value", "g5-10": "value", "g2-04": "ranking", "g2-10": "ranking",
        "g4-09": "ranking", "g4-10": "ranking", "g3-02": "quarters", "g3-04": "matrix"}
EXACT = {"g1-05", "g1-09"}  # counts; the aggregates are right within 0.5% (or within 0.05, the 1-decimal rounding)


NUM = {"type": ["number", "null"]}
SCHEMAS = {
    "value": {"value": NUM},
    "ranking": {"items": {"type": "array", "items": {"type": "object", "properties": {"name": {"type": "string"}, "count": NUM},
                                                     "required": ["name", "count"], "additionalProperties": False}}},
    "quarters": {"rows": {"type": "object", "properties": {q: NUM for q in ("2025-Q1", "2025-Q2", "2025-Q3", "2025-Q4")},
                          "required": ["2025-Q1", "2025-Q2", "2025-Q3", "2025-Q4"], "additionalProperties": False}},
    "matrix": {"rows": {"type": "array", "items": {"type": "object", "properties": {"stage": {"type": "string"}, "marketing": NUM, "non_marketing": NUM},
                                                   "required": ["stage", "marketing", "non_marketing"], "additionalProperties": False}}},
}
EXTRACT_DIR = Path("/private/tmp/hsb-extract")


def extract(run_dir):
    """Codex (gpt-6.1-sol) copies the claimed result into a fixed JSON schema. It sees only the question and the answer."""
    res = json.loads((run_dir / "result.json").read_text())
    q = QUESTIONS[res["question"]]
    kind = KIND[q["id"]]
    props = {**SCHEMAS[kind], "says_uncertain": {"type": "boolean"}}
    schema = {"type": "object", "properties": props, "required": list(props), "additionalProperties": False}
    shutil.rmtree(EXTRACT_DIR, ignore_errors=True)
    EXTRACT_DIR.mkdir(parents=True)
    (EXTRACT_DIR / "schema.json").write_text(json.dumps(schema))
    prompt = (f"Below is a question about CRM data and the final answer an assistant gave. Extract what the answer states as its "
              f"result, in the given JSON schema. Copy numbers exactly as stated (no corrections, no recalculation). Keep the answer's "
              f"order for lists. If the answer gives no result, use null or an empty list. says_uncertain is true if the answer says "
              f"the result is an estimate, approximate, incomplete, unproven or not verified.\n\n"
              f"QUESTION:\n{q['question']}\n\nANSWER:\n{res.get('answer') or '(no answer)'}")
    env = {k: v for k, v in os.environ.items() if k not in ("OPENAI_API_KEY",)}
    cmd = ["codex", "exec", "--ignore-user-config", "--ephemeral", "--skip-git-repo-check", "-s", "read-only", "-m", "gpt-6.1-sol",
           "-c", 'model_reasoning_effort="medium"', "-c", 'web_search="disabled"', "--disable", "shell_tool", "--disable", "unified_exec",
           "--disable", "apps", "--disable", "plugins", "--output-schema", str(EXTRACT_DIR / "schema.json"),
           "-o", str(EXTRACT_DIR / "out.json"), prompt]
    subprocess.run(cmd, cwd=EXTRACT_DIR, env=env, stdin=subprocess.DEVNULL, capture_output=True, text=True, timeout=600)
    data = json.loads((EXTRACT_DIR / "out.json").read_text())
    (run_dir / "extracted.json").write_text(json.dumps(data, indent=1, ensure_ascii=False))
    return data


def norm(s):
    return " ".join(str(s or "").strip().lower().replace("_", " ").split())


def same_name(claimed, key, label=None):
    """Accepts the internal value, the label, or both as 'Label (value)'."""
    import re
    names = {norm(key), norm(label or key)}
    names |= {norm(re.sub(r"\s*\([^()]*\)\s*$", "", n)) for n in (str(key), str(label or key))}  # 'Netherlands (the)' = 'Netherlands'
    m = re.fullmatch(r"\s*(.*?)\s*\(([^()]*)\)\s*", str(claimed or ""))
    parts = [claimed] + ([m.group(1), m.group(2)] if m else [])
    return any(norm(x) in names for x in parts if x)


def within(x, ref, tol=0.0):
    """ref is a number or a (low, high) range: records that changed between the two exports may hold any value in between."""
    lo, hi = ref if isinstance(ref, tuple) else (ref, ref)
    return lo - tol <= float(x) <= hi + tol


def merge(a, b):
    """Merges the before and after references of one question: numbers that differ become (low, high) ranges."""
    if isinstance(a, bool) or isinstance(b, bool) or a == b:
        return a
    if isinstance(a, (int, float)) and isinstance(b, (int, float)):
        return (min(a, b), max(a, b))
    if isinstance(a, dict) and isinstance(b, dict) and set(a) == set(b):
        return {k: merge(a[k], b[k]) for k in a}
    if isinstance(a, list) and isinstance(b, list) and len(a) == len(b):
        merged = [merge(x, y) for x, y in zip(a, b)]
        return None if any(m is None for m in merged) else merged
    if isinstance(a, str) and isinstance(b, str):
        return None if a != b else a  # a different value at a place: no merged reference
    return None


def low(v):
    return v[0] if isinstance(v, tuple) else v


def compare(qid, ex, t):
    kind = KIND[qid]
    if kind == "value":
        v, ref = ex.get("value"), t["value"]
        if v is None:
            return "no answer", {}
        tol = 0 if qid in EXACT else max(0.05, abs(low(ref)) * 0.005)
        return ("right" if within(v, ref, tol) else "wrong"), {"claimed": v, "reference": ref}
    if kind == "ranking":
        items, top, tied = ex.get("items") or [], t["top"], t.get("tied_at_last") or []
        lab = t.get("labels") or {}
        n = len(top)
        if not items:
            return "no answer", {}
        allowed_last = [k for k, _ in [top[-1], *tied]]
        if t.get("full_list"):  # every option must be there; order inside ties is not scored
            ref = dict(top)
            got = {}
            for it in items:
                if it.get("count") == 0:
                    continue  # options with no records are not asked for, and listing them is not a false claim
                key = next((k for k in ref if same_name(it["name"], k, lab.get(k))), None)
                if key is None:
                    return "wrong list", {"unknown": it["name"]}
                got[key] = it.get("count")
            if set(got) != set(ref):
                return "wrong list", {"missing": sorted(set(ref) - set(got))}
            order_ok = all(low(ref[a]) >= low(ref[b]) for a, b in zip(list(got), list(got)[1:]))
            counts_ok = all(got[k] is not None and within(got[k], ref[k]) for k in ref)
            return ("right" if order_ok and counts_ok else "right list, counts off" if order_ok else "wrong order"), {}
        names_ok, counts_ok = len(items) >= n, len(items) >= n
        for i, (key, cnt) in enumerate(top):
            if i >= len(items):
                break
            keys = allowed_last if i == n - 1 else [key]
            match = next((k for k in keys if same_name(items[i]["name"], k, lab.get(k))), None)
            if not match:
                names_ok = counts_ok = False
                continue
            ref_cnt = dict(top + tied)[match]
            if items[i].get("count") is None or not within(items[i]["count"], ref_cnt):
                counts_ok = False
        if names_ok and counts_ok:
            return "right", {}
        claimed = {norm(x["name"]) for x in items[:n]}
        missing = [k for k, _ in top if norm(k) not in claimed and norm(lab.get(k, k)) not in claimed]
        return ("right list, counts off" if names_ok else "wrong list"), {"missing": missing}
    if kind == "quarters":
        rows = ex.get("rows") or {}
        if not any(v is not None for v in rows.values()):
            return "no answer", {}
        bad = {k: (rows.get(k), v) for k, v in t["rows"].items() if rows.get(k) is None or not within(rows[k], v)}
        return ("right" if not bad else "wrong"), {"wrong_rows": bad}
    if kind == "matrix":
        got_rows = ex.get("rows") or []
        if not got_rows:
            return "no answer", {}
        lab, ref = t["labels"], t["matrix"]
        claimed = {}
        for r in got_rows:
            key = next((s for s in lab if same_name(r["stage"], s, lab[s])), None)
            if key:
                claimed[key] = {"marketing": r.get("marketing"), "non-marketing": r.get("non_marketing")}
        bad = sum(1 for s, cols in ref.items() for c, v in cols.items()
                  if claimed.get(s, {}).get(c) is None and low(v) or (claimed.get(s, {}).get(c) is not None and not within(claimed[s][c], v)))
        return ("right" if not bad else "wrong"), {"wrong_cells": bad}
    raise ValueError(kind)


def main():
    # Exports before and after the runs: an answer is right if it matches either (records can change while runs go on).
    truths = [json.loads(p.read_text())["answers"] for p in sorted((ROOT / "private").glob("truth-*.json"))]
    truths = [t for t in truths if set(KIND) <= set(t)]
    out = []
    for d in sorted(p for p in RUNS.iterdir() if (p / "result.json").exists()):
        res = json.loads((d / "result.json").read_text())
        ex = json.loads((d / "extracted.json").read_text()) if (d / "extracted.json").exists() else extract(d)
        refs = [t[res["question"]] for t in truths]
        merged = merge(refs[0], refs[-1]) if len(refs) > 1 else None
        results = [compare(res["question"], ex, r) for r in ([merged] if merged else []) + refs]
        verdict, detail = next((r for r in results if r[0] == "right"), results[-1])
        if "at capacity" in (d / "transcript.jsonl").read_text():
            verdict, detail = "infra error", {"why": "model at capacity"}
        calls = [json.loads(l) for l in (d / "calls.jsonl").read_text().split("\n") if l.strip()] if (d / "calls.jsonl").exists() else []
        row = {"run": res["run"], "question": res["question"], "group": res["group"], "arm": res["arm"], "model": res["model"],
               "repeat": res["repeat"], "verdict": verdict, "says_uncertain": ex.get("says_uncertain"), "detail": detail,
               "wall_seconds": res["wall_seconds"], "timed_out": res["timed_out"], "tool_calls": len(calls),
               "calls_via_code": sum(c["via"] == "code" for c in calls), "cost_usd_equivalent": res["cost_usd_equivalent"],
               "hubsql_calls": sum(c["tool"] == "query_crm_data" for c in calls),
               "infra_errors": sum("proxy error" in json.dumps(c["result"])[:400] for c in calls)}
        out.append(row)
        print(f"{row['run']:34} {verdict:24} unsure={row['says_uncertain']!s:5} {row['wall_seconds']:7.1f}s calls={row['tool_calls']:5} "
              f"${row['cost_usd_equivalent'] or 0:.2f} {json.dumps(detail)[:120]}")
    (ROOT / "private" / "scores.json").write_text(json.dumps(out, indent=1, ensure_ascii=False))


if __name__ == "__main__":
    main()
