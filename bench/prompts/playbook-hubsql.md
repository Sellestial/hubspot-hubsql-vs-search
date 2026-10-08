
How to answer analytical questions with query_crm_data (HubSQL, private beta):

- Call tool_guidance for query_crm_data first and follow it. Confirm property names (search_properties) and option values (get_properties) before writing a query.
- A count: SELECT COUNT(*) with the filters.
- A ranking or breakdown: GROUP BY (at most 2 columns), ORDER BY the count DESC. Grouped counts can come back slightly low when LIMIT is small, so ask for more rows than you need (LIMIT 100 or more) and keep the top N.
- Every count you report must be exact: check each reported count with a separate filtered COUNT(*). Check the boundary: also check the row just below your last place.
- If the definition normalizes values (for example trims spaces or ignores capitalization), check how GROUP BY and = compare values before you trust a count.
- Multi-select fields: check how GROUP BY treats records with several values before you trust a per-option count.
- Dates: DATE_TRUNC(property, 'MONTH'), property first; in aggregations, filter dates with YYYY-MM-DD values.
- Averages and medians: AVG(...) and MEDIAN(...) (MEDIAN not with GROUP BY); also report how many records had a value (COUNT(property)).
- If you could not verify a ranking, say so.
- Always say which numbers are exact and which are not.
