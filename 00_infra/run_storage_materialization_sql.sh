#!/usr/bin/env bash
set -euo pipefail

FLINK_CONTAINER="${FLINK_CONTAINER:-smtrend-flink-jobmanager}"

cat \
  03_storage/01_materialization/01_storage_source_and_sink_tables.sql \
  03_storage/01_materialization/02_materialize_silver.sql \
  | docker exec -i "${FLINK_CONTAINER}" /opt/flink/bin/sql-client.sh embedded
