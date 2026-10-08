"""Minimal client for HubSpot's remote MCP server (streamable HTTP), authenticated as the OAuth user."""
import asyncio, json, os, time
from contextlib import asynccontextmanager

from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client
from mcp.shared._httpx_utils import create_mcp_http_client

from bench.oauth import access_token

MCP_URL = os.environ.get("HUBSPOT_MCP_URL", "https://mcp.hubspot.com/")


@asynccontextmanager
async def session():
    client = create_mcp_http_client(headers={"Authorization": f"Bearer {access_token()}"})
    async with client, streamable_http_client(MCP_URL, http_client=client) as streams:
        read, write = streams[0], streams[1]
        async with ClientSession(read, write) as s:
            await s.initialize()
            yield s


async def list_tools():
    async with session() as s:
        res = await s.list_tools()
        return [t.model_dump(mode="json", exclude_none=True) for t in res.tools]


async def call(name, args):
    """Calls one tool; returns (result as plain JSON-able dict, seconds)."""
    async with session() as s:
        t = time.monotonic()
        res = await s.call_tool(name, args)
        return res.model_dump(mode="json", exclude_none=True), round(time.monotonic() - t, 2)


if __name__ == "__main__":
    import sys
    if sys.argv[1] == "tools":
        print(json.dumps(asyncio.run(list_tools()), indent=1))
    elif sys.argv[1] == "call":
        out, secs = asyncio.run(call(sys.argv[2], json.loads(sys.argv[3] if len(sys.argv) > 3 else "{}")))
        print(json.dumps({"seconds": secs, "result": out}, indent=1))
