# Experiment v2: search vs HubSQL, redesigned

Status 2026-10-07: design, not yet run. The v1 runs (5 questions) become pilot data and are not scored.

Why v2: Codex (gpt-6-sol) red-teamed v1 and found 14 weaknesses. The author's rule: we fix a weakness in the experiment, we don't explain it away in the text. Each row below is one weakness and its fix.

| # | Weakness in v1 | Fix in v2 |
|---|---|---|
| 1 | Our copies of the MCP tools (own descriptions, rewritten and clipped results, no `tool_guidance`, private app token) | The real HubSpot MCP server (mcp.hubspot.com) via OAuth as the author; tool names, descriptions and schemas from its `tools/list`, saved with the results |
| 2 | Search could not run code | Code arms: the same MCP tools callable from Anthropic's code execution (programmatic tool calling), so the agent can page through everything and add up in code |
| 3 | The search agent's approach was weak (no sampling) | Expert arms with a written playbook for each tool, frozen before the runs, no answers or candidate titles in it |
| 4 | HubSQL's description had extra help (`DATE_TRUNC` order) | Plain arms use the server's own descriptions unchanged; extra help only in the expert playbooks, for both tools |
| 5 | HubSQL was the ground truth although its counts can be low | Ground truth from our own full export (scripted, no AI), aggregated offline, taken before and after the runs; HubSQL is scored against it like any arm |
| 6 | The 5 questions were picked by us after exploring | A pool of 30+ questions written before any run, in 5 groups; a recorded random seed picks 2 per group; the pool is published |
| 7 | Loose definitions (nulls, ties, "2026" in October) | Each question has a fixed definition: cutoff date, null handling, exact vs normalized values, ties, rounding |
| 8 | "25 steps" was model turns, not calls; clipped JSON | A 15-minute wall-time limit per run, no clipping (paged results), stop reason logged |
| 9 | Few repeats, one model | 3 runs of every question in every arm; a second model (Sonnet 5.5) on the main arms |
| 10 | Timing shaped by our fixed sleeps and serial calls | One shared rate limiter at HubSpot's limits (search 5/s, HubSQL 1/s), parallel calls allowed, `429` handled; model time and HubSpot time logged apart |
| 11 | "Per 100 questions" cost was an extrapolation | Report measured cost and time per question group; no per-100 headline |
| 12 | The manual sampling check was done after seeing the miss | Removed; the expert and code arms test this properly |
| 13 | Logs too thin to audit | Full transcripts, raw tool results, HTTP status, a run manifest (private), plus an aggregate summary (public) |
| 14 | One portal | Claims stay about our portal; stated in the caveats (we have no second portal with HubSQL) |

## Arms

All arms: Claude Opus 5.5, the same short system prompt and business definitions, the real MCP server's read-only tools, 15-minute limit.

| Arm | Tools | What it tests |
|---|---|---|
| S | real MCP read tools except `query_crm_data` | Claude connected to HubSpot today, without HubSQL |
| S-expert | same, plus a frozen search playbook (sample in strata, count candidates exactly, partition under 10,000, say what is proven) | whether a weak approach caused the misses |
| S-code | same tools, callable from code execution | the strongest search setup |
| Q | real MCP read tools incl. `query_crm_data` | Claude connected to HubSpot with HubSQL |
| Q-expert | same, plus a frozen HubSQL playbook (dialect, LIMIT, verify counts) | whether HubSQL's quirks can be managed |
| Q-code | same tools, callable from code execution | a matched pair for S-code |

Anthropic's MCP connector tools can't be called from code, so our own MCP client proxies the server's tools as custom tools with the same definitions, for every arm. Same OAuth user everywhere.

## Questions

Groups: simple counts, rankings over a dropdown, breakdowns by time and category, rankings over free text, averages or sums. Pool of 30+ written before any run, 2 per group picked by seed, 10 in total. Contacts and companies only (our portal has few deals).

## Runs and budget

- Opus 5.5: 10 questions x 6 arms x 3 runs = 180 runs. Sonnet 5.5: S, S-expert, Q x 2 runs = 60 runs.
- Order randomized within each question block.
- Estimate: $60-90 in model cost (no-code search runs are the expensive part, about $0.60-1.00 each); live meter, stop at $100.
- HubSpot load: full scans in the code arms are about 2,454 search pages (titles) and 905 (company size) each; at 5/s that is 3-8 minutes per scan. Well inside our daily API limits.

## Scoring

Per run: exact complete answer; ranking membership and order separately from counts; abstained / flagged uncertainty / wrong with confidence; tool calls; wall time (model, HubSpot, waits); model cost.

Decision rule, fixed now: if S-code is exact and S fails, the result is "HubSQL matters for AI assistants without code", not "search can't do it". If both code arms are exact, HubSQL's advantage is speed and cost, and we report it that way. If Q gets counts wrong, it is scored wrong, whatever its speed.

## Setup needed

1. HubSpot: Development > MCP Connectors > Create MCP connector (name, redirect URL `http://localhost:6274/oauth/callback`). Gives a client ID and secret.
2. One OAuth consent in the browser (PKCE), as the author.
3. Question pool review.

## Deviations and findings during the runs (2026-10-07)

1. **Test agents: Codex instead of Claude.** The author chose Codex CLI with gpt-6.1-sol, reasoning effort xhigh, for all 6 arms (180 runs, 11:02-17:03 UTC).
2. **Codex calls MCP tools only from JavaScript (code mode).** Found after the runs: one no-code search run received 9.3 million characters of tool results with 405,000 input tokens in total. A probe confirmed that with `code_mode_host` off, Codex has no HubSpot tool at all. So all 6 Codex arms could compute in code; the "code" arms additionally had a shell and a Python helper. The Codex results stand for coding agents, not for chat assistants.
3. **No-code condition added on Claude Sonnet 5.5** (the author's decision): search, search + playbook, HubSQL, HubSQL + playbook, 10 questions x 3 runs, `claude -p` with no built-in tools; MCP results go into the conversation. Same proxy, questions, prompts, time limit and scoring.
4. **Infrastructure errors:** 3 Codex runs failed with "Selected model is at capacity"; they are kept in private/failed-runs and were run again.
5. **Records changed during the runs** (3 records in one question). For a number that differs between the exports, any value between them counts as right.
6. **Claude Sonnet 5.5 with code added** after the first article review (Codex: the code effect was confounded with the model). Search + shell and HubSQL + shell, 60 runs, 20:25-21:35 UTC. Result: search 29/30, HubSQL 28/30 (without code: 19/30 and 28/30).
7. **MCP-layer behavior found while explaining wrong answers** (all verified directly): through the MCP server, both search EQ and HubSQL `=` return 13,564 for state 'California' (incl. 'Estado de Baja California'); the REST APIs return 13,563. Through the MCP server, a grouped HubSQL query treats the end date as a whole day (`< '2026-10-01'`: plain count 86, grouped 90); REST HubSQL returns 86 both ways.
8. **Scoring fixes** (no answer changed): names written as 'Label (value)' and labels without HubSpot's '(the)' suffix are accepted; options listed with 0 records are ignored; call logs are split on newlines only (a Unicode line separator inside a job title broke one line).
