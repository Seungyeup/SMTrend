#!/usr/bin/env bash
set -euo pipefail

if ! curl -sS -H "Content-Type: application/json" -d '{"query":"SELECT COUNT(*) AS c FROM market_bar_1m"}' "http://localhost:8082/druid/v2/sql" >/dev/null 2>&1; then
  echo "Druid visualization bootstrap precheck failed: datasource 'market_bar_1m' is not queryable yet." >&2
  echo "Make sure 05_serving is RUNNING and curated.market.bar.1m.v1 has produced queryable rows in Druid before bootstrapping Superset on Druid." >&2
  exit 1
fi

docker exec \
  -e SUPERSET_DB_NAME="Druid Market" \
  -e SUPERSET_DB_URI="druid://host.docker.internal:8082/druid/v2/sql" \
  -e SUPERSET_DATASET_CATALOG="" \
  -e SUPERSET_DATASET_SCHEMA="" \
  -e SUPERSET_DATASET_TABLE="market_bar_1m_druid" \
  -e SUPERSET_PHYSICAL_TABLE="market_bar_1m" \
  -e SUPERSET_DASHBOARD_TITLE="SMTrend Druid Monitoring" \
  -e SUPERSET_TABLE_CHART_NAME="Druid market bars by symbol" \
  -e SUPERSET_TIMESERIES_CHART_NAME="Druid 1-minute close price over time" \
  -e SUPERSET_TIME_COLUMN="__time" \
  smtrend-superset python /app/bootstrap/bootstrap_superset_content.py
