"""Call the HubSpot tools from Python (code arms). Same tools, same definitions, same limits as the tool calls.

    from hubspot import call
    res = call("search_crm_objects", {"objectType": "COMPANY", "limit": 200, "properties": ["name"]})

call() returns the tool's result: the JSON the tool returns, parsed (a str if it isn't JSON).
Raises RuntimeError with the tool's message when the tool reports an error.
"""
import base64, http.client, json, os, urllib.parse, urllib.request

_RUN, _ARM = os.environ["BENCH_RUN"], os.environ["BENCH_ARM"]
_DAEMON = os.environ.get("BENCH_DAEMON", "http://127.0.0.1:8799")


def call_raw(tool, arguments=None):
    body = json.dumps({"run": _RUN, "arm": _ARM, "tool": tool, "args": arguments or {}, "via": "code"}).encode()
    proxy = os.environ.get("HTTP_PROXY") or os.environ.get("http_proxy")
    if not proxy:  # outside a sandbox: connect directly
        req = urllib.request.Request(_DAEMON, data=body, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=620) as r:
            return json.loads(r.read())
    # In Claude Code's sandbox only its HTTP proxy may connect, also for localhost (which NO_PROXY would bypass).
    p = urllib.parse.urlparse(proxy)
    headers = {"Content-Type": "application/json"}
    if p.username:
        cred = f"{urllib.parse.unquote(p.username)}:{urllib.parse.unquote(p.password or '')}"
        headers["Proxy-Authorization"] = "Basic " + base64.b64encode(cred.encode()).decode()
    conn = http.client.HTTPConnection(p.hostname, p.port, timeout=620)
    conn.request("POST", _DAEMON.rstrip("/") + "/", body=body, headers=headers)
    r = conn.getresponse()
    data = r.read()
    if r.status != 200:
        raise RuntimeError(f"proxy returned HTTP {r.status}: {data[:200]!r}")
    return json.loads(data)


def call(tool, arguments=None):
    res = call_raw(tool, arguments)
    text = "\n".join(c.get("text", "") for c in res.get("content", []) if c.get("type") == "text")
    if res.get("isError"):
        raise RuntimeError(text)
    try:
        return json.loads(text)
    except ValueError:
        return text
