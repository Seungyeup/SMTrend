#!/usr/bin/env bash
set -euo pipefail

pid_file="${MARKET_MOCK_PID_FILE:-tmp/market_mock.pid}"
log_file="${MARKET_MOCK_LOG_FILE:-tmp/market_mock.log}"
superset_url="${SUPERSET_URL:-http://172.30.1.40:8088}"

bash scripts/bootstrap_kafka_topics.sh
bash scripts/request_druid_ingestion.sh
bash scripts/apply_druid_retention.sh

until curl -fsS "${superset_url}/health" >/dev/null; do
  sleep 2
done

mkdir -p "$(dirname "${pid_file}")"
if [[ -f "${pid_file}" ]]; then
  current_pid="$(cat "${pid_file}")"
  if [[ -n "${current_pid}" ]] && ps -p "${current_pid}" >/dev/null 2>&1; then
    echo "Continuous market producer is already running (pid=${current_pid})."
    echo "Superset monitoring stack is active."
    echo "Superset URL: ${superset_url}"
    exit 0
  fi
fi

nohup bash scripts/run_market_mock.sh >"${log_file}" 2>&1 &
echo "$!" >"${pid_file}"

echo "Superset monitoring stack is active."
echo "Superset URL: ${superset_url}"
echo "Continuous market producer started (pid=$(cat "${pid_file}"), log=${log_file})."
