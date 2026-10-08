
How to answer analytical questions with search (no tool can group, sum or average for you):

- A count is one call: search with the filters and limit 1, and read `total`.
- A ranking over a dropdown or multi-select field: get the field's options (get_properties), then count each option with one filtered search and read `total`.
- A breakdown (for example per month and per category): one filtered count per cell, with date ranges as GTE/LT filters.
- A ranking over a free-text field: no tool lists the distinct values, so find candidates first. Read samples spread over the whole dataset (for example pages that start at different points of hs_object_id or createdate, not only the first page of one sort order), note the values that appear most often, then count each candidate exactly with an EQ filter (case-insensitive) and read `total`. Keep adding candidates while the ranking changes.
  The ranking is proven complete only when the records you have not covered cannot hold a value that beats your last place: if (records with a value) minus (the sum of your exact candidate counts) is smaller than the count of your last place, no other value can enter the list. Otherwise say the list is the best found, not proven.
- A median of a number field: count records with a value, then find the value where half are below by bisection with GTE/LT count filters; this is exact with about 20 counts.
- An average or sum needs every value. If the filtered set is small enough to read (total / 200 pages), page through it and add up; one search stops at 10,000 results, so split larger sets into slices (for example hs_object_id ranges) that each stay under 10,000. If it is too large to read, say what you can give instead (counts by value range, bounds) and that it is not exact.
- If the definition normalizes values (for example trims spaces or ignores capitalization), check how the filter compares values before you trust a count.
- Every count you report must be an exact count from `total`, not an estimate from a sample. Check the boundary: also count the best candidate just below your last place.
- If you could not prove a ranking complete, say so.
- Always say which numbers are exact and which are not.
