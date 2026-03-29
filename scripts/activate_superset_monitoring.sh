#!/usr/bin/env bash
set -euo pipefail

pid_file="${MARKET_MOCK_PID_FILE:-tmp/market_mock.pid}"
log_file="${MARKET_MOCK_LOG_FILE:-tmp/market_mock.log}"

pick_superset_port() {
  if [[ -n "${SUPERSET_HOST_PORT:-}" ]]; then
    echo "${SUPERSET_HOST_PORT}"
    return
  fi

  for candidate in 8088 18088 28088; do
    if ! lsof -nP -iTCP:"${candidate}" -sTCP:LISTEN >/dev/null 2>&1; then
      echo "${candidate}"
      return
    fi
  done

  echo "No available Superset host port in [8088, 18088, 28088]. Set SUPERSET_HOST_PORT explicitly." >&2
  exit 1
}

export SUPERSET_HOST_PORT="$(pick_superset_port)"

bootstrap_superset_content() {
  local retries="${SUPERSET_BOOTSTRAP_RETRIES:-30}"
  local delay_s="${SUPERSET_BOOTSTRAP_RETRY_DELAY_S:-2}"
  local attempt

  for ((attempt = 1; attempt <= retries; attempt += 1)); do
    if docker compose exec -T superset python - < scripts/bootstrap_superset_content.py; then
      return 0
    fi
    echo "Superset content bootstrap failed (attempt ${attempt}/${retries}), retrying in ${delay_s}s..."
    sleep "${delay_s}"
  done

  echo "Superset content bootstrap failed after ${retries} attempts." >&2
  exit 1
}

docker compose --profile core --profile storage --profile compute --profile query --profile serving --profile bi up -d

bash scripts/bootstrap_kafka_topics.sh
bash scripts/submit_flink_sql.sh
bash scripts/request_druid_ingestion.sh
bash scripts/apply_druid_retention.sh

until curl -fsS "http://localhost:${SUPERSET_HOST_PORT}/health" >/dev/null; do
  sleep 2
done

bootstrap_superset_content

mkdir -p "$(dirname "${pid_file}")"
if [[ -f "${pid_file}" ]]; then
  current_pid="$(cat "${pid_file}")"
  if [[ -n "${current_pid}" ]] && ps -p "${current_pid}" >/dev/null 2>&1; then
    echo "Continuous market producer is already running (pid=${current_pid})."
    echo "Superset monitoring stack is active."
    echo "Superset URL: http://localhost:${SUPERSET_HOST_PORT}"
    exit 0
  fi
fi

nohup bash scripts/run_market_mock.sh >"${log_file}" 2>&1 &
echo "$!" >"${pid_file}"

echo "Superset monitoring stack is active."
echo "Superset URL: http://localhost:${SUPERSET_HOST_PORT}"
echo "Continuous market producer started (pid=$(cat "${pid_file}"), log=${log_file})."
