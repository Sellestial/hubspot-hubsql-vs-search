# Question selection

Pool: 50 questions written by a separate AI agent that saw only the field list (docs/question-pool.json).

## Eligibility rules (fixed before selection; they look only at definitions, never at answers)

- **E1**: Every named field and option exists in the portal. An option named by a wrong label is corrected to the existing option with the same meaning; if none exists, the question is out.
- **E2**: No moving or unknown time reference (for example 'in the last 30 days' relative to an enrichment run).
- **E3**: Sellestial fields only (no fields of a second brand that shares the portal).
- **E4**: No answer that names a person or reveals named companies or domains from our prospect list, because the answers are published.
- **E5**: Not a repeat of one of the five v1 pilot questions (job titles, average company size, top industries, contacts per month, companies without a domain): the test must be held out. Added on reviewer advice after the first draw and before any scored run; the first draw is kept in docs/selection-first-draw.md.

## Excluded

- g1-03 (E5): How many company records don't have a domain?
- g1-08 (E3): (redacted: uses fields of a second brand in the same portal)
- g2-03 (E5): What are the top 10 industries among our companies?
- g2-08 (E2): Which 10 countries have the most contacts who posted on LinkedIn in the last 30 days? Use the Country/Region Code field.
- g2-09 (E3): (redacted: uses fields of a second brand in the same portal)
- g3-01 (E5): How many contacts did we create each month from January to September 2026?
- g3-09 (E2): Cross-tab our RevOps persona contacts against whether they posted on LinkedIn in the last 30 days.
- g4-01 (E5): What are the 10 most common job titles in our contact database?
- g4-05 (E4): Which company names show up most often on our contacts? Top 10.
- g4-07 (E4): Which company names appear on the most company records? Show the top 10 so we can spot duplicates.
- g4-08 (E4): Which 10 domains are shared by the most company records?
- g5-01 (E5): What's the average number of employees across our companies?
- g5-04 (E4): Which contact has the most LinkedIn followers, and how many followers is that?
- g5-05 (E3): (redacted: uses fields of a second brand in the same portal)
- g5-07 (E3): (redacted: uses fields of a second brand in the same portal)

## Corrected

- g5-08: label 'United States' -> label 'United States of America (the)'

## Selection: seed 20261007, Python random.Random(seed).sample, 2 per group in id order

- g1-05 (count): How many contacts have RevOps or Revenue Operations in their job title?
- g1-09 (count): How many companies were founded in 2020 or later?
- g2-04 (dropdown-ranking): Which 10 HQ countries have the most ICP companies?
- g2-10 (dropdown-ranking): Rank the latest traffic sources for contacts whose latest source date falls in September 2026.
- g3-02 (breakdown): How many company records were created in each quarter of 2025?
- g3-04 (breakdown): For each lifecycle stage, how many contacts are marketing contacts and how many are not?
- g4-09 (free-text-ranking): Which 10 states have the most companies with country code US?
- g4-10 (free-text-ranking): What are the 10 most common industries on our contacts? I mean the contact-level Industry field.
- g5-09 (aggregate): How many sessions in total have contacts from paid social generated?
- g5-10 (aggregate): What's the average SEO score of companies that run HubSpot according to BuiltWith?
