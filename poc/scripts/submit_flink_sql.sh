#!/usr/bin/env bash
set -euo pipefail

FLINK_K8S_NAMESPACE="${FLINK_K8S_NAMESPACE:-smtrend}"
FLINK_SQL_CLIENT_POD="${FLINK_SQL_CLIENT_POD:-}"
FLINK_SUBMIT_MODE="${FLINK_SUBMIT_MODE:-full}"
FLINK_PARALLELISM="${FLINK_PARALLELISM:-1}"

if [[ -z "${FLINK_SQL_CLIENT_POD}" ]]; then
  FLINK_SQL_CLIENT_POD="$(kubectl -n "${FLINK_K8S_NAMESPACE}" get pods -l app=flink,component=jobmanager -o jsonpath='{.items[0].metadata.name}' 2>/dev/null || true)"
fi

if [[ -z "${FLINK_SQL_CLIENT_POD}" ]]; then
  echo "Flink jobmanager pod not found in namespace ${FLINK_K8S_NAMESPACE}." >&2
  exit 1
fi

if ! command -v kubectl >/dev/null 2>&1; then
  echo "kubectl is required for Kubernetes Flink SQL submission." >&2
  exit 1
fi

kubectl -n "${FLINK_K8S_NAMESPACE}" exec "${FLINK_SQL_CLIENT_POD}" -- mkdir -p /tmp/flink-jars

for jar in \
  flink/lib/flink-sql-connector-kafka-3.1.0-1.18.jar \
  flink/lib/flink-parquet-1.18.1.jar \
  flink/lib/parquet-hadoop-bundle-1.13.1.jar \
  flink/lib/hadoop-mapreduce-client-core-3.3.6.jar; do
  if [[ -f "${jar}" ]]; then
    kubectl -n "${FLINK_K8S_NAMESPACE}" cp "${jar}" "${FLINK_SQL_CLIENT_POD}:/tmp/flink-jars/$(basename "${jar}")"
  fi
done

tmp_file="/tmp/flink_poc_all.sql"
{
  echo "SET 'parallelism.default' = '${FLINK_PARALLELISM}';"
  echo "SET 'table.exec.resource.default-parallelism' = '${FLINK_PARALLELISM}';"

  echo "ADD JAR 'file:///tmp/flink-jars/flink-sql-connector-kafka-3.1.0-1.18.jar';"
  echo "ADD JAR 'file:///tmp/flink-jars/flink-parquet-1.18.1.jar';"
  echo "ADD JAR 'file:///tmp/flink-jars/parquet-hadoop-bundle-1.13.1.jar';"
  echo "ADD JAR 'file:///tmp/flink-jars/hadoop-mapreduce-client-core-3.3.6.jar';"
  echo "ADD JAR 'file:///opt/flink/opt/flink-s3-fs-hadoop-1.18.1.jar';"

  if [[ "${FLINK_SUBMIT_MODE}" == "market-poc" ]]; then
    cat flink/sql/01_tables.sql
    cat flink/sql/02_market_bar_1m.sql
    cat flink/sql/06_market_only_materialization.sql
  elif [[ "${FLINK_SUBMIT_MODE}" == "minimal" ]]; then
    cat flink/sql/01_tables.sql
    cat flink/sql/05_silver_materialization.sql
  else
    cat flink/sql/01_tables.sql
    cat flink/sql/02_market_bar_1m.sql
    cat flink/sql/03_macro_state.sql
    cat flink/sql/04_enriched_analytics.sql
    cat flink/sql/05_silver_materialization.sql
  fi
} > "${tmp_file}"

kubectl -n "${FLINK_K8S_NAMESPACE}" cp "${tmp_file}" "${FLINK_SQL_CLIENT_POD}:/tmp/flink_poc_all.sql"
kubectl -n "${FLINK_K8S_NAMESPACE}" exec "${FLINK_SQL_CLIENT_POD}" -- \
  /opt/flink/bin/sql-client.sh -f /tmp/flink_poc_all.sql

echo "Flink SQL statements submitted via Kubernetes pod ${FLINK_SQL_CLIENT_POD}."
