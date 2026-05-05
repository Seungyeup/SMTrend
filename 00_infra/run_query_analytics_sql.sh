#!/usr/bin/env bash
set -euo pipefail

TRINO_STATEMENT_URL="${TRINO_STATEMENT_URL:-http://localhost:8080/v1/statement}"
TRINO_USER="${TRINO_USER:-airflow}"

python3 00_infra/run_trino_sql_http.py \
  --trino-statement-url "${TRINO_STATEMENT_URL}" \
  --user "${TRINO_USER}" \
  --catalog hive \
  --schema market \
  --sql-file 04_query/02_analytics_queries/01_market_macro_correlation.sql \
  --print-rows
