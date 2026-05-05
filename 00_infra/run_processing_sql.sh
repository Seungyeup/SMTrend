#!/usr/bin/env bash
set -euo pipefail

FLINK_CONTAINER="${FLINK_CONTAINER:-smtrend-flink-jobmanager}"

cat \
  02_processing/01_common/01_source_and_sink_tables.sql \
  02_processing/02_market/02_market_bar_1m.sql \
  02_processing/03_macro/03_macro_latest_state.sql \
  02_processing/04_analytics/04_market_macro_enriched.sql \
  | docker exec -i "${FLINK_CONTAINER}" /opt/flink/bin/sql-client.sh embedded
