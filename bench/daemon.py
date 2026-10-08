"""Local service between the test agents and HubSpot's remote MCP server.

Holds one MCP session (OAuth user), checks each call against the run's arm, paces calls at HubSpot's limits,
and logs every call with its raw result and timing to private/runs/<run>/calls.jsonl.

  uv run python -m bench.daemon            # listens on 127.0.0.1:8799
"""
import asyncio, json, threading, time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from bench.arms import ARMS, DEFAULT_INTERVAL, MIN_INTERVAL
from bench.mcp_client import session

ROOT = Path(__file__).resolve().parent.parent
RUNS = ROOT / "private" / "runs"
PORT = 8799


class Upstream:
    """One MCP session in a background event loop; reconnects (with a fresh token) when a call fails."""

    def __init__(self):
        self.loop = asyncio.new_event_loop()
        threading.Thread(target=self.loop.run_forever, daemon=True).start()
        self.sess, self.ctx, self.connected_at = None, None, 0.0
        self.last = {}  # tool family -> monotonic time of the last call start
        self.lock = asyncio.Lock()

    async def _connect(self):
        if self.ctx:
            try:
                await self.ctx.__aexit__(None, None, None)
            except Exception:  # noqa: BLE001
                pass
        self.ctx = session()
        self.sess = await self.ctx.__aenter__()
        self.connected_at = time.time()

    async def _pace(self, tool):
        interval = MIN_INTERVAL.get(tool, DEFAULT_INTERVAL)
        async with self.lock:
            now = time.monotonic()
            wait = max(0.0, self.last.get(tool, 0) + interval - now)
            self.last[tool] = now + wait
        if wait:
            await asyncio.sleep(wait)
        return wait

    async def _call(self, tool, args):
        wait = await self._pace(tool)
        for attempt in range(3):
            try:
                if self.sess is None or time.time() - self.connected_at > 1200:  # OAuth access tokens live ~30 min
                    async with self.lock:
                        if self.sess is None or time.time() - self.connected_at > 1200:
                            await self._connect()
                t = time.monotonic()
                res = await self.sess.call_tool(tool, args)
                return res.model_dump(mode="json", by_alias=True, exclude_none=True), round(time.monotonic() - t, 3), wait, attempt
            except Exception as exc:  # noqa: BLE001
                err = exc
                self.sess = None
                await asyncio.sleep(2 * (attempt + 1))
        return {"content": [{"type": "text", "text": f"proxy error: {err!s:.300}"}], "isError": True}, 0.0, wait, 3

    def call(self, tool, args):
        return asyncio.run_coroutine_threadsafe(self._call(tool, args), self.loop).result(timeout=600)


UP = Upstream()
LOG_LOCK = threading.Lock()


class Handler(BaseHTTPRequestHandler):
    def do_POST(self):
        req = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        run, arm, tool, args, via = req["run"], req["arm"], req["tool"], req.get("args") or {}, req.get("via", "direct")
        t0 = time.time()
        if tool not in ARMS[arm]["tools"]:
            result, secs, wait, retries = {"content": [{"type": "text", "text": f"Unknown tool: {tool}"}], "isError": True}, 0.0, 0.0, 0
        else:
            result, secs, wait, retries = UP.call(tool, args)
        rec = {"ts": t0, "tool": tool, "via": via, "args": args, "seconds": secs, "throttle_wait": round(wait, 3),
               "retries": retries, "is_error": bool(result.get("isError")), "result": result}
        d = RUNS / run
        d.mkdir(parents=True, exist_ok=True)
        with LOG_LOCK, open(d / "calls.jsonl", "a") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
        body = json.dumps(result, ensure_ascii=False).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *a):
        pass


if __name__ == "__main__":
    print(f"listening on 127.0.0.1:{PORT}", flush=True)
    ThreadingHTTPServer(("127.0.0.1", PORT), Handler).serve_forever()
