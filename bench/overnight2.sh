#!/bin/bash
# No-code arms on Claude Sonnet 5.5, then exports, reference answers and scoring. Writes private/overnight2.done at the end.
cd "$(dirname "$0")/.." || exit 1
LOG=private/overnight2.log
echo "start $(date -u +%FT%TZ)" >> $LOG
uv run python -m bench.run --all --model sonnet --arms S,S-expert,Q,Q-expert --repeats 3 >> $LOG 2>&1
echo "runs done $(date -u +%FT%TZ)" >> $LOG
uv run python -m bench.export contacts jobtitle,hs_latest_source,hs_latest_source_timestamp,lifecyclestage,hs_marketable_status,industry,hs_analytics_source,hs_analytics_num_visits > private/export-contacts-after2.log 2>&1 &
uv run python -m bench.export companies founded_year,sellestial_icp,hq_country_linkedin,createdate,hs_country_code,state,builtwith_contains_hubspot,sellestial_seo_score > private/export-companies-after2.log 2>&1 &
wait
uv run python -m bench.truth >> $LOG 2>&1
uv run python -m bench.score > private/scores.log 2>&1
echo "all done $(date -u +%FT%TZ)" >> $LOG
touch private/overnight2.done
