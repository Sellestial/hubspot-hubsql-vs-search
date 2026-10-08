"""Claude answers questions about the Sellestial HubSpot portal with (S) HubSpot's search tool or (Q) HubSQL,
mirroring the tools of HubSpot's remote MCP server (search_crm_objects: filters, <=200 per page, total count;
query_crm_data: SQL without joins). Read-only. Results go to ai_test.json."""
import json, sys, time
from pathlib import Path
import anthropic, httpx

ROOT = Path(__file__).parent
env = dict(l.split("=", 1) for l in Path.home().joinpath(".config/jevbench/env").read_text().splitlines() if "=" in l and not l.startswith("#"))
H = {"Authorization": f"Bearer {env['HUBSPOT_TOKEN'].strip().strip(chr(34)).strip(chr(39))}"}
ai_env = dict(l.split("=", 1) for l in Path.home().joinpath(".config/ai-posting/env").read_text().splitlines() if "=" in l and not l.startswith("#"))
client = anthropic.Anthropic(api_key=ai_env["ANTHROPIC_API_KEY"].strip(), max_retries=4, timeout=300)
MODEL, PRICE = "claude-opus-5-5", (4.0, 20.0)
OBJS = ["contacts", "companies", "deals", "emails", "notes", "meetings", "calls", "tasks"]
CAP = 40000

def clip(obj):
    s = json.dumps(obj, ensure_ascii=False)
    return s if len(s) <= CAP else s[:CAP] + ' ... [truncated: result too long]'

def search_crm_objects(objectType, filterGroups=None, query=None, properties=None, sorts=None, limit=100, after=None):
    body = {"limit": max(1, min(int(limit or 100), 200))}
    if filterGroups: body["filterGroups"] = filterGroups
    if query: body["query"] = query
    if properties: body["properties"] = properties
    if sorts: body["sorts"] = sorts
    if after: body["after"] = after
    r = httpx.post(f"https://api.hubapi.com/crm/v3/objects/{objectType}/search", headers=H, json=body, timeout=60); time.sleep(0.3)
    b = r.json()
    if r.status_code != 200:
        return clip({"error": b.get("message", str(b))[:500]})
    return clip({"total": b.get("total"), "results": [{"id": x["id"], **{k: v for k, v in x.get("properties", {}).items() if v not in (None, "")}} for x in b.get("results", [])],
                 "next_after": ((b.get("paging") or {}).get("next") or {}).get("after")})

def search_properties(objectType, keyword):
    r = httpx.get(f"https://api.hubapi.com/crm/v3/properties/{objectType}", headers=H, timeout=60); time.sleep(0.3)
    if r.status_code != 200:
        return clip({"error": r.text[:300]})
    kw = keyword.lower()
    hits = [p for p in r.json().get("results", []) if kw in p["name"].lower() or kw in (p.get("label") or "").lower()][:30]
    return clip([{"name": p["name"], "label": p.get("label"), "type": p.get("type"),
                  "options": [(o["value"], o["label"]) for o in p.get("options", [])][:300]} for p in hits])

def query_crm_data(query, after=None):
    if "JOIN" in query.upper():
        return clip({"error": "query_crm_data does not support joins"})
    body = {"query": query, "pageSize": 100}
    if after: body["after"] = after
    r = httpx.post("https://api.hubapi.com/analytics/hubsql/2027-03-beta/query", headers=H, json=body, timeout=60); time.sleep(1.1)
    b = r.json()
    if r.status_code != 200:
        return clip({"error": b.get("message", str(b))[:500]})
    return clip({"total": b.get("total"), "results": b.get("results"), "next_after": ((b.get("paging") or {}).get("next") or {}).get("after")})

FILTER = {"type": "object", "properties": {"propertyName": {"type": "string"}, "operator": {"type": "string", "enum": ["EQ", "NEQ", "LT", "LTE", "GT", "GTE", "BETWEEN", "IN", "NOT_IN", "HAS_PROPERTY", "NOT_HAS_PROPERTY", "CONTAINS_TOKEN", "NOT_CONTAINS_TOKEN"]}, "value": {"type": "string"}, "highValue": {"type": "string"}, "values": {"type": "array", "items": {"type": "string"}}}, "required": ["propertyName", "operator"]}
TOOLS = {
 "search_crm_objects": {"name": "search_crm_objects", "description": "Search HubSpot CRM records of one object type with filters (up to 5 filter groups, 6 filters each, groups are ORed), an optional text query, sorting and pagination. Returns up to 200 records per call, the total number of matching records, and a cursor for the next page.",
   "input_schema": {"type": "object", "properties": {"objectType": {"type": "string", "enum": OBJS}, "filterGroups": {"type": "array", "items": {"type": "object", "properties": {"filters": {"type": "array", "items": FILTER}}, "required": ["filters"]}}, "query": {"type": "string"}, "properties": {"type": "array", "items": {"type": "string"}}, "sorts": {"type": "array", "items": {"type": "object", "properties": {"propertyName": {"type": "string"}, "direction": {"type": "string", "enum": ["ASCENDING", "DESCENDING"]}}, "required": ["propertyName", "direction"]}}, "limit": {"type": "integer"}, "after": {"type": "string"}}, "required": ["objectType"]}},
 "search_properties": {"name": "search_properties", "description": "Find CRM property definitions (internal name, label, type, options) of an object type by keyword.",
   "input_schema": {"type": "object", "properties": {"objectType": {"type": "string", "enum": OBJS}, "keyword": {"type": "string"}}, "required": ["objectType", "keyword"]}},
 "query_crm_data": {"name": "query_crm_data", "description": "Query HubSpot CRM data using SQL with HubSpot-specific extensions. Supports filtering, aggregation (COUNT, SUM, AVG, MIN, MAX, MEDIAN, GROUP BY up to 2 columns) and sorting. Dates: DATE_TRUNC(property, 'MONTH') (the property comes first; units DAY, WEEK, MONTH, QUARTER, YEAR); you can alias it and GROUP BY the alias. Tables: OBJECT.CONTACT, OBJECT.COMPANY, OBJECT.DEAL, OBJECT.EMAIL, OBJECT.NOTE, OBJECT.MEETING_EVENT, OBJECT.CALL, OBJECT.TASK. Does not support joins, subqueries or arithmetic. Returns up to 100 rows per page.",
   "input_schema": {"type": "object", "properties": {"query": {"type": "string"}, "after": {"type": "string"}}, "required": ["query"]}},
}
IMPL = {"search_crm_objects": search_crm_objects, "search_properties": search_properties, "query_crm_data": query_crm_data}
MODES = {"S": ["search_crm_objects", "search_properties"], "Q": ["query_crm_data", "search_properties"]}
SYSTEM = "You are an assistant connected to our company's HubSpot CRM through tools. Answer the user's question about our CRM data with exact numbers."
QUESTIONS = {
 "C1": "What are the 10 most common job titles among our contacts, and how many contacts have each?",
 "C2": "What is the average number of employees of the companies in our CRM?",
 "C3": "Which 10 industries have the most companies in our CRM, and how many companies each?",
 "C4": "How many new contacts did we add in each month of 2026, broken down by how they were created (record source)?",
 "C5": "How many of our companies have no domain?",
}
MAX_TURNS = 25

def run(qid, mode):
    tools = [TOOLS[n] for n in MODES[mode]]
    messages = [{"role": "user", "content": QUESTIONS[qid]}]
    calls, tin, tout, cr, cw = [], 0, 0, 0, 0
    t0 = time.monotonic()
    for turn in range(MAX_TURNS):
        r = client.messages.create(model=MODEL, max_tokens=8000, system=SYSTEM, tools=tools, messages=messages,
                                   cache_control={"type": "ephemeral"})
        u = r.usage; tin += u.input_tokens; tout += u.output_tokens
        cr += getattr(u, "cache_read_input_tokens", 0) or 0; cw += getattr(u, "cache_creation_input_tokens", 0) or 0
        messages.append({"role": "assistant", "content": r.content})
        uses = [b for b in r.content if b.type == "tool_use"]
        if r.stop_reason != "tool_use" or not uses:
            break
        results = []
        for b in uses:
            try:
                out = IMPL[b.name](**b.input)
            except Exception as exc:  # noqa: BLE001
                out = json.dumps({"error": str(exc)[:300]})
            calls.append({"tool": b.name, "input": b.input, "result_chars": len(out)})
            results.append({"type": "tool_result", "tool_use_id": b.id, "content": out})
        messages.append({"role": "user", "content": results})
    answer = "\n".join(b.text for b in r.content if b.type == "text")
    cost = (tin * PRICE[0] + cw * PRICE[0] * 1.25 + cr * PRICE[0] * 0.1 + tout * PRICE[1]) / 1e6
    return {"qid": qid, "mode": mode, "answer": answer, "tool_calls": calls, "turns": turn + 1, "seconds": round(time.monotonic() - t0, 1),
            "tokens": {"in": tin, "out": tout, "cache_read": cr, "cache_write": cw}, "cost": round(cost, 4)}

if __name__ == "__main__":
    out_path = ROOT / "ai_test2.json"
    done = json.loads(out_path.read_text()) if out_path.exists() else []
    have = {(d["qid"], d["mode"]) for d in done}
    for qid in QUESTIONS:
        for mode in ("S", "Q"):
            if (qid, mode) in have:
                continue
            res = run(qid, mode)
            done.append(res)
            out_path.write_text(json.dumps(done, indent=1, default=str))
            print(f"{qid} {mode}: {len(res['tool_calls'])} calls, {res['seconds']} s, ${res['cost']:.3f} | {res['answer'][:300]!r}", flush=True)
    print("total cost: $%.2f" % sum(d["cost"] for d in done))
