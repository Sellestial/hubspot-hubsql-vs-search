# Results summary

360 scored runs, 7-8 October 2026. Right answers out of 30 per setup (10 questions x 3 runs).

| Setup | Right | Median seconds | Median tool calls |
|---|---|---|---|
| Claude, no code, search | 19/30 | 38 | 12 |
| Claude, no code, HubSQL | 28/30 | 10 | 3 |
| Claude with code, search | 29/30 | 85 | 80 |
| Claude with code, HubSQL | 28/30 | 13 | 2 |
| Codex, search | 30/30 | 118 | 62 |
| Codex, HubSQL | 28/30 | 36 | 6 |
| Claude, no code, search + guide | 22/30 | 34 | 16 |
| Claude, no code, HubSQL + guide | 25/30 | 18 | 6 |
| Codex, search + guide | 26/30 | 92 | 30 |
| Codex, HubSQL + guide | 29/30 | 53 | 15 |
| Codex, search + shell | 30/30 | 110 | 114 |
| Codex, HubSQL + shell | 28/30 | 40 | 6 |

## Per question (right out of 3)

| Question | Claude, no code, search | Claude, no code, HubSQL | Claude with code, search | Claude with code, HubSQL | Codex, search | Codex, HubSQL |
|---|---|---|---|---|---|---|
| g1-05 How many contacts have RevOps or Revenue Operations in their | 0/3, 46 s | 1/3, 92 s | 2/3, 155 s | 2/3, 143 s | 3/3, 129 s | 1/3, 32 s |
| g1-09 How many companies were founded in 2020 or later? | 3/3, 31 s | 3/3, 10 s | 3/3, 46 s | 3/3, 41 s | 3/3, 151 s | 3/3, 32 s |
| g2-04 Which 10 HQ countries have the most ICP companies? | 3/3, 54 s | 3/3, 9 s | 3/3, 107 s | 3/3, 12 s | 3/3, 123 s | 3/3, 41 s |
| g2-10 Rank the latest traffic sources for contacts whose latest so | 3/3, 22 s | 3/3, 8 s | 3/3, 27 s | 2/3, 8 s | 3/3, 37 s | 3/3, 59 s |
| g3-02 How many company records were created in each quarter of 202 | 3/3, 9 s | 3/3, 15 s | 3/3, 10 s | 3/3, 12 s | 3/3, 24 s | 3/3, 33 s |
| g3-04 For each lifecycle stage, how many contacts are marketing co | 3/3, 40 s | 3/3, 8 s | 3/3, 66 s | 3/3, 8 s | 3/3, 53 s | 3/3, 35 s |
| g4-09 Which 10 states have the most companies with country code US | 0/3, 44 s | 3/3, 9 s | 3/3, 146 s | 3/3, 14 s | 3/3, 261 s | 3/3, 62 s |
| g4-10 What are the 10 most common industries on our contacts? I me | 0/3, 48 s | 3/3, 12 s | 3/3, 191 s | 3/3, 18 s | 3/3, 301 s | 3/3, 163 s |
| g5-09 How many sessions in total have contacts from paid social ge | 3/3, 14 s | 3/3, 9 s | 3/3, 24 s | 3/3, 9 s | 3/3, 24 s | 3/3, 31 s |
| g5-10 What's the average SEO score of companies that run HubSpot a | 1/3, 30 s | 3/3, 12 s | 3/3, 142 s | 3/3, 11 s | 3/3, 184 s | 3/3, 32 s |

Verdicts: right; wrong; wrong list; right list, counts off; wrong order; no answer. See bench/score.py for the rules.
