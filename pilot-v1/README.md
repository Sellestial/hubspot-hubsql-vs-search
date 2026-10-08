# First test (v1), replaced

The first version of the test, kept for the record. It is not part of the scored results.

- Claude Opus 5.5 through the Anthropic API, with hand-written copies of HubSpot's MCP tools (`search_crm_objects`, `search_properties`, `query_crm_data`) that called HubSpot's REST APIs with a private app token, and no code execution.
- Five questions chosen by the author after exploring the portal (job titles, average company size, top industries, contacts per month by source, companies without a domain).
- HubSQL's own results were used as the correct answers.

Its conclusion was that search fails at anything beyond simple counts. A review by Codex ([../docs/reviews/1-design-review-of-the-first-test.md](../docs/reviews/1-design-review-of-the-first-test.md)) found, among other things, that the tools were not HubSpot's real ones, that the agent could not run code, that the questions were picked by the author, and that HubSQL's grouped counts can be low with a small LIMIT, so HubSQL could not be the reference. v2 fixed each point.

Files: `ai_test2.py` (the agent harness), `run.py` and `truth2.py` (HubSQL queries used for the reference). They read the token from `~/.config/jevbench/env`.
