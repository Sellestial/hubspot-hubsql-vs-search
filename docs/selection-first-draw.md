# Question selection

Pool: 50 questions written by a separate AI agent that saw only the field list (docs/question-pool.json).

## Eligibility rules (fixed before selection; they look only at definitions, never at answers)

- **E1**: Every named field and option exists in the portal. An option named by a wrong label is corrected to the existing option with the same meaning; if none exists, the question is out.
- **E2**: No moving or unknown time reference (for example 'in the last 30 days' relative to an enrichment run).
- **E3**: Sellestial fields only (no fields of a second brand that shares the portal).
- **E4**: No answer that names a person or reveals named companies or domains from our prospect list, because the answers are published.

## Excluded

- g1-08 (E3): (redacted: uses fields of a second brand in the same portal)
- g2-08 (E2): Which 10 countries have the most contacts who posted on LinkedIn in the last 30 days? Use the Country/Region Code field.
- g2-09 (E3): (redacted: uses fields of a second brand in the same portal)
- g3-09 (E2): Cross-tab our RevOps persona contacts against whether they posted on LinkedIn in the last 30 days.
- g4-05 (E4): Which company names show up most often on our contacts? Top 10.
- g4-07 (E4): Which company names appear on the most company records? Show the top 10 so we can spot duplicates.
- g4-08 (E4): Which 10 domains are shared by the most company records?
- g5-04 (E4): Which contact has the most LinkedIn followers, and how many followers is that?
- g5-05 (E3): (redacted: uses fields of a second brand in the same portal)
- g5-07 (E3): (redacted: uses fields of a second brand in the same portal)

## Corrected

- g5-08: label 'United States' -> label 'United States of America (the)'

## Selection: seed 20261007, Python random.Random(seed).sample, 2 per group in id order

- g1-04 (count): How many companies headquartered in Germany (LinkedIn HQ country) have between 50 and 500 employees?
- g1-06 (count): How many contacts does Koalify flag as having at least one duplicate?
- g2-02 (dropdown-ranking): What were the top 5 original traffic sources for contacts created between January and September 2026?
- g2-03 (dropdown-ranking): What are the top 10 industries among our companies?
- g3-02 (breakdown): How many company records were created in each quarter of 2025?
- g3-03 (breakdown): Split the contacts created in July, August and September 2026 by original traffic source, per month.
- g4-02 (free-text-ranking): Which 10 countries have the most contacts, going by the Country/Region text field?
- g4-10 (free-text-ranking): What are the 10 most common industries on our contacts? I mean the contact-level Industry field.
- g5-02 (aggregate): What's the median employee count of our ICP companies?
- g5-10 (aggregate): What's the average SEO score of companies that run HubSpot according to BuiltWith?
