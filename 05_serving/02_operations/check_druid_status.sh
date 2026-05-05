#!/usr/bin/env bash
set -euo pipefail

DRUID_API_URL="${DRUID_API_URL:-http://localhost:8888}"
DRUID_SUPERVISOR_ID="${DRUID_SUPERVISOR_ID:-market_bar_1m}"

curl -sS "${DRUID_API_URL}/druid/indexer/v1/supervisor/${DRUID_SUPERVISOR_ID}/status"
