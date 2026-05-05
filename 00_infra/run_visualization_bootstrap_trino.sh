#!/usr/bin/env bash
set -euo pipefail

if ! docker exec smtrend-trino bash -lc "trino --server http://localhost:8080 --execute \"SELECT count(*) FROM hive.market.market_bar_1m\"" >/dev/null 2>&1; then
  echo "Trino visualization bootstrap precheck failed: hive.market.market_bar_1m is not queryable yet." >&2
  echo "Make sure hive-metastore is up and 03_storage/04_query path is healthy before bootstrapping Superset on Trino." >&2
  exit 1
fi

docker exec \
  -e SUPERSET_DB_NAME="Trino Market" \
  -e SUPERSET_DB_URI="trino://trino@host.docker.internal:8080/hive/market" \
  -e SUPERSET_DATASET_CATALOG="hive" \
  -e SUPERSET_DATASET_SCHEMA="market" \
  -e SUPERSET_DATASET_TABLE="market_bar_1m_trino" \
  -e SUPERSET_PHYSICAL_TABLE="market_bar_1m" \
  -e SUPERSET_DASHBOARD_TITLE="SMTrend Monitoring" \
  -e SUPERSET_TABLE_CHART_NAME="Market bars by symbol (Trino)" \
  -e SUPERSET_TIMESERIES_CHART_NAME="1-minute close price over time (Trino)" \
  -e SUPERSET_TIME_COLUMN="bucket_1m_utc" \
  smtrend-superset python /app/bootstrap/bootstrap_superset_content.py
