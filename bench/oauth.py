"""OAuth 2.1 (PKCE) for HubSpot's remote MCP server, as the user who clicks "Connect".

  uv run python -m bench.oauth login     # prints the authorize URL, waits for the redirect on localhost:6274
  uv run python -m bench.oauth token     # prints a fresh access token's expiry (refreshes when needed)

Credentials (MCP_CLIENT_ID, MCP_CLIENT_SECRET) come from the env file; tokens are saved next to it, mode 600.
"""
import base64, hashlib, http.server, json, os, secrets, sys, time, urllib.parse
from pathlib import Path

import httpx

ENV_FILE = Path(os.environ.get("HUBSQL_BENCH_ENV", Path.home() / ".config/hubsql-bench/env"))
TOKEN_FILE = ENV_FILE.with_name("hubspot-mcp-token.json")
AUTHORIZE_URL = "https://mcp-eu1.hubspot.com/oauth/authorize/user"  # what HubSpot's install URL builder shows for our EU portal
TOKEN_URLS = ["https://mcp-eu1.hubspot.com/oauth/v3/token", "https://mcp.hubspot.com/oauth/v3/token"]
REDIRECT = "http://localhost:6274/oauth/callback"


def env():
    return {k.strip(): v.strip().strip('"').strip("'") for k, v in
            (l.split("=", 1) for l in ENV_FILE.read_text().splitlines() if "=" in l and not l.startswith("#"))}


def _save(tok):
    tok["expires_at"] = time.time() + int(tok.get("expires_in", 1800)) - 60
    TOKEN_FILE.touch(mode=0o600)
    TOKEN_FILE.write_text(json.dumps(tok, indent=1))
    os.chmod(TOKEN_FILE, 0o600)
    return tok


def _token_request(data):
    e = env()
    data = {**data, "client_id": e["MCP_CLIENT_ID"], "client_secret": e["MCP_CLIENT_SECRET"]}
    last = None
    for url in TOKEN_URLS:
        r = httpx.post(url, data=data, timeout=30)
        if r.status_code == 200:
            return r.json()
        last = f"{url}: {r.status_code} {r.text[:300]}"
    raise RuntimeError(f"token request failed: {last}")


def login():
    verifier = secrets.token_urlsafe(64)[:96]
    challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b"=").decode()
    state = secrets.token_urlsafe(16)
    url = AUTHORIZE_URL + "?" + urllib.parse.urlencode({
        "client_id": env()["MCP_CLIENT_ID"], "redirect_uri": REDIRECT, "response_type": "code",
        "code_challenge": challenge, "code_challenge_method": "S256", "state": state})
    print(url, flush=True)
    got = {}

    class Handler(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            q = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
            got.update({k: v[0] for k, v in q.items()})
            self.send_response(200)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.end_headers()
            self.wfile.write(b"Connected. You can close this tab." if "code" in got else b"No code received.")

        def log_message(self, *a):
            pass

    srv = http.server.HTTPServer(("127.0.0.1", 6274), Handler)
    srv.timeout = 900
    while "code" not in got and "error" not in got:
        srv.handle_request()
    if got.get("state") != state:
        sys.exit(f"state mismatch or error: {got.get('error')} {got.get('error_description', '')}")
    tok = _save(_token_request({"grant_type": "authorization_code", "code": got["code"],
                                "redirect_uri": REDIRECT, "code_verifier": verifier}))
    print("saved token, expires in", int(tok["expires_at"] - time.time()), "s; refresh token:", "yes" if tok.get("refresh_token") else "no")


def access_token():
    """A valid access token; refreshes it when it is about to expire."""
    tok = json.loads(TOKEN_FILE.read_text())
    if time.time() >= tok["expires_at"]:
        new = _token_request({"grant_type": "refresh_token", "refresh_token": tok["refresh_token"]})
        new.setdefault("refresh_token", tok["refresh_token"])
        tok = _save(new)
    return tok["access_token"]


if __name__ == "__main__":
    if sys.argv[1:] == ["login"]:
        login()
    else:
        access_token()
        print("token ok, expires in", int(json.loads(TOKEN_FILE.read_text())["expires_at"] - time.time()), "s")
