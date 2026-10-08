# HubSpot search vs HubSQL for AI agents

Code, questions and results for a test of AI agents answering CRM questions through HubSpot's remote MCP server, once with the search tools only and once with HubSQL (`query_crm_data`) added. 360 scored runs on Sellestial's own HubSpot portal (about 500,000 contacts and 230,000 companies), October 2026.

Written at [Sellestial](https://sellestial.com), a HubSpot services company. Not affiliated with HubSpot; HubSQL beta access came through the request link in HubSpot's product updates.

## Results

Right answers out of 30 (10 questions x 3 runs). "Search": HubSpot's search tools only. "HubSQL": the same tools plus HubSQL.

| Agent | Search | HubSQL |
|---|---|---|
| Claude Sonnet 5.5, no code (tool results go into the conversation) | 19 | 28 |
| Claude Sonnet 5.5 with code (a sandboxed shell that calls the same tools from Python) | 29 | 28 |
| Codex CLI, GPT-6.1 Sol at extra-high reasoning (calls MCP tools from JavaScript, so it always has code) | 30 | 28 |

- Without code, search fell behind: the agent could only estimate top 10s over free-text fields and averages over tens of thousands of records.
- With code, search caught up, but on the five heaviest questions it took 8 to 13 times longer (Claude: 54 to 524 tool calls against 1 to 3).
- 29 of the 38 wrong answers were on two questions where a filter returned more records than a literal match, with search and with HubSQL:
  - `LIKE '%revenue operations%'` returned 8,920 contacts; the literal phrase is in 8,147 job titles (matches include "Director of Revenue Cycle Operations"). 15 runs reported 10,347 contacts with RevOps or Revenue Operations in the title; the right number was 9,574.
  - Through the MCP server, `state = 'California'` (search and HubSQL) returned 13,564 US companies, including one in "Estado de Baja California". HubSpot's REST APIs return 13,563.
- Through the MCP server, a grouped HubSQL query treated the end date as a whole day: `< '2026-10-01'` returned 86 contacts as a plain count and 90 when grouped (October 1 included). REST HubSQL returned 86 both ways.
- Claude flagged doubt in 26 of its 29 wrong answers; GPT-6.1 Sol in none of its 9.

All setups, including the ones with a written guide or an extra shell, are in [results/summary.md](results/summary.md). Every run is in [results/runs.csv](results/runs.csv), with the extracted answer and verdict in [results/answers.jsonl](results/answers.jsonl) and the reference answers in [results/reference.json](results/reference.json).

## How it was tested

- **HubSpot's remote MCP server** (mcp.hubspot.com) through an MCP connector, OAuth as a user, read-only tools. Each agent reached it through a small local proxy ([bench/daemon.py](bench/daemon.py), [bench/stdio_proxy.py](bench/stdio_proxy.py)) that checks the setup's tool list, logs every call and passes HubSpot's tool definitions on unchanged ([results/mcp-tools.json](results/mcp-tools.json)).
- **Questions.** A separate AI wrote a pool of 50 questions from the portal's field list ([docs/question-pool.json](docs/question-pool.json)). Written rules removed 15, and seed 20261007 drew two from each of five groups ([docs/selection.md](docs/selection.md)). One rule (no repeats of the first test's questions) was added after a first draw and before any scored run; the first draw is kept.
- **Same input for every setup:** the same system prompt ([bench/prompts](bench/prompts)), the question and its exact scoring definition, a 20-minute limit, 3 fresh runs, arm order randomized per question.
- **Reference answers** from full exports of every contact and company through the REST search API (script, no AI), taken before, during and after the runs ([bench/export.py](bench/export.py), [bench/truth.py](bench/truth.py)). Three records changed during the day; where a number changed between exports, any value between them counted as right.
- **Scoring.** Codex copied each final answer into a fixed JSON shape without knowing the setup; code compared it with the reference ([bench/score.py](bench/score.py)).
- **Isolation.** Agents with a shell ran in a macOS sandbox without access to credentials, other runs' files or the reference data ([bench/agent.sb](bench/agent.sb) for Codex, Claude Code's sandbox for Claude).

The full design, deviations and findings during the runs are in [docs/experiment-v2.md](docs/experiment-v2.md).

## The first test, and why it was replaced

The first version ([pilot-v1](pilot-v1)) used hand-written copies of HubSpot's tools, an agent without code, and five questions chosen by the author. Its conclusion ("search fails beyond simple counts") did not survive review. The reviews that shaped this version are in [docs/reviews](docs/reviews).

## Reproduce it

Requirements: macOS (for the Codex sandbox), Python 3.10+, [uv](https://docs.astral.sh/uv/), a HubSpot portal with HubSQL beta access, Claude Code and/or the Codex CLI.

1. In HubSpot: Development > MCP Connectors > Create MCP connector, redirect URL `http://localhost:6274/oauth/callback`.
2. Put the credentials in `~/.config/hubsql-bench/env` (or point `HUBSQL_BENCH_ENV` at another file): `MCP_CLIENT_ID`, `MCP_CLIENT_SECRET`, and `HUBSPOT_TOKEN` (a private app token with read scopes, used only for the reference export).
3. Run:

```bash
uv sync
uv run python -m bench.oauth login                 # open the printed URL, choose the portal, connect
uv run python -m bench.mcp_client tools > results/mcp-tools.json
uv run python -m bench.daemon &                    # the proxy, 127.0.0.1:8799
uv run python -m bench.export contacts <fields>    # reference exports (see bench/truth.py for the fields)
uv run python -m bench.export companies <fields>
uv run python -m bench.run --all --model sonnet --arms S,Q --repeats 3          # Claude, no code
uv run python -m bench.run --all --model sonnet --arms S-code,Q-code --repeats 3  # Claude with code
uv run python -m bench.run_codex --all --repeats 3                                # Codex
uv run python -m bench.truth && uv run python -m bench.score
```

`bench/overnight*.sh` are the exact sequences used. The questions and their definitions are portal-specific; for another portal, write a new pool and selection with `bench/select_questions.py`.

## Caveats

- One portal, mostly prospect data. 10 questions, two models.
- Claude ran in Claude Code; Claude.ai or ChatGPT may present tool results differently.
- Times include the models' thinking; Codex ran at extra-high reasoning effort.
- The agents saw the exact scoring definition with each question.
- Transcripts and raw tool results are not published, because they contain CRM records.

## License

MIT
