# Follow-up check: "equals" on company state (October 8, 2026)

In the 360 runs, `state = 'California'` through the MCP server (HubSQL and the search tool) returned 13,564 US companies, one more than HubSpot's REST APIs: the extra company has the state "Estado de Baja California". One record is easy to miss, so after the runs I checked a state name that is contained in another one: "Virginia" and "West Virginia".

Script: [bench/check_equals.py](../bench/check_equals.py) (read-only). Output: [results/check-equals.json](../results/check-equals.json).

US companies (`hs_country_code` = US) per state filter:

| Filter | MCP server, search tool (`search_crm_objects`, EQ) | REST search API (EQ) |
|---|---|---|
| state = "Virginia" | 2,175 | 2,105 |
| state = "West Virginia" | 70 | 70 |
| state = "California" | 13,564 | 13,563 |

Through the MCP server, "equals Virginia" also counted all 70 companies in West Virginia (2,105 + 70 = 2,175). The REST API matched exactly.

HubSQL (`query_crm_data`) returned "Unknown RPC service error" for every query that day, including `SELECT COUNT(*) FROM company`, so this check covers the MCP search tool only. In the 360 runs, HubSQL's `=` and the search tool's EQ gave the same California count.
