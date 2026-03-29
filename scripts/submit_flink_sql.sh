#!/usr/bin/env bash
set -euo pipefail

for jar in flink/lib/*.jar; do
  docker compose cp "${jar}" flink-jobmanager:/opt/flink/lib/
  docker compose cp "${jar}" flink-taskmanager:/opt/flink/lib/
done

docker compose restart flink-jobmanager flink-taskmanager

until curl -sSf http://localhost:8082/overview >/dev/null; do
  sleep 1
done

tmp_file="/tmp/flink_poc_all.sql"
cat \
  flink/sql/01_tables.sql \
  flink/sql/02_market_bar_1m.sql \
  flink/sql/03_macro_state.sql \
  flink/sql/04_enriched_analytics.sql \
  flink/sql/05_hdfs_materialization.sql > "${tmp_file}"

docker compose cp "${tmp_file}" flink-jobmanager:/tmp/flink_poc_all.sql
docker compose exec -T \
  -e HADOOP_CONF_DIR=/etc/hadoop/conf \
  -e HADOOP_CLASSPATH=/opt/flink/hadoop-libs/* \
  flink-jobmanager /opt/flink/bin/sql-client.sh -f /tmp/flink_poc_all.sql

echo "Flink SQL statements submitted in one session file."
