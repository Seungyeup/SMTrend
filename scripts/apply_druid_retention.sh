#!/usr/bin/env bash
set -euo pipefail

DRUID_API_URL="${DRUID_API_URL:-http://localhost:8083}"
DRUID_DATASOURCE="${DRUID_DATASOURCE:-market_bar_1m}"
DRUID_RETENTION_DAYS="${DRUID_RETENTION_DAYS:-30}"
DRUID_DEFAULT_TIER_REPLICAS="${DRUID_DEFAULT_TIER_REPLICAS:-1}"

if ! [[ "${DRUID_RETENTION_DAYS}" =~ ^[0-9]+$ ]] || [[ "${DRUID_RETENTION_DAYS}" -le 0 ]]; then
  echo "DRUID_RETENTION_DAYS must be a positive integer, got '${DRUID_RETENTION_DAYS}'" >&2
  exit 1
fi

rules_payload=$(cat <<EOF
[
  {
    "type": "loadByPeriod",
    "period": "P${DRUID_RETENTION_DAYS}D",
    "includeFuture": true,
    "tieredReplicants": {
      "_default_tier": ${DRUID_DEFAULT_TIER_REPLICAS}
    }
  },
  {
    "type": "dropForever"
  }
]
EOF
)

curl -sS -X POST \
  -H "Content-Type: application/json" \
  -d "${rules_payload}" \
  "${DRUID_API_URL}/druid/coordinator/v1/rules/${DRUID_DATASOURCE}" >/dev/null

echo "Applied Druid retention rules: datasource=${DRUID_DATASOURCE}, retention_days=${DRUID_RETENTION_DAYS}"
