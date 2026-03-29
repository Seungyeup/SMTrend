#!/usr/bin/env bash
set -euo pipefail

DRUID_API_URL="${DRUID_API_URL:-http://localhost:8083}"

curl -X POST \
  -H "Content-Type: application/json" \
  -d @druid/specs/market_bar_1m_kafka.json \
  "${DRUID_API_URL}/druid/indexer/v1/supervisor"
