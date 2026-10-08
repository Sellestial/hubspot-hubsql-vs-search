"""Which real HubSpot MCP tools each arm gets. Read-only tools only; definitions come unchanged from the server."""

# Read tools of HubSpot's remote MCP server that matter for CRM questions (tools/list, 2026-10-07).
READ_TOOLS = [
    "tool_guidance", "get_user_details", "get_organization_details", "discover_hubspot_schema",
    "search_crm_objects", "get_crm_objects", "search_properties", "get_properties", "search_owners",
]
SEARCH_TOOLS = READ_TOOLS
HUBSQL_TOOLS = READ_TOOLS + ["query_crm_data"]

ARMS = {
    "S": {"tools": SEARCH_TOOLS, "code": False, "playbook": None},
    "S-expert": {"tools": SEARCH_TOOLS, "code": False, "playbook": "search"},
    "S-code": {"tools": SEARCH_TOOLS, "code": True, "playbook": None},
    "Q": {"tools": HUBSQL_TOOLS, "code": False, "playbook": None},
    "Q-expert": {"tools": HUBSQL_TOOLS, "code": False, "playbook": "hubsql"},
    "Q-code": {"tools": HUBSQL_TOOLS, "code": True, "playbook": None},
}

# Minimum seconds between calls, shared by all runs (HubSpot's documented limits: search 5/s, HubSQL 1/s).
MIN_INTERVAL = {"search_crm_objects": 0.2, "get_crm_objects": 0.2, "query_crm_data": 1.0}
DEFAULT_INTERVAL = 0.1
