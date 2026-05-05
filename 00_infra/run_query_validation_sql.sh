#!/usr/bin/env bash
set -euo pipefail

TRINO_STATEMENT_URL="${TRINO_STATEMENT_URL:-http://localhost:8080/v1/statement}"
TRINO_USER="${TRINO_USER:-airflow}"

python3 00_infra/run_trino_sql_http.py \
  --trino-statement-url "${TRINO_STATEMENT_URL}" \
  --user "${TRINO_USER}" \
  --catalog hive \
  --schema market \
  --sql-file 04_query/03_validation/01_validate_external_tables.sql \
  --print-rows

python3 00_infra/run_trino_sql_http.py \
  --trino-statement-url "${TRINO_STATEMENT_URL}" \
  --user "${TRINO_USER}" \
  --catalog hive \
  --schema market \
  --sql-file 04_query/03_validation/02_validate_gold_tables.sql \
  --print-rows
