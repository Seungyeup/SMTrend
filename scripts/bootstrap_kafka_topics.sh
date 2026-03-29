#!/usr/bin/env bash
set -euo pipefail

RAW_MARKET_RETENTION_DAYS="${RAW_MARKET_RETENTION_DAYS:-7}"
RAW_MACRO_RETENTION_DAYS="${RAW_MACRO_RETENTION_DAYS:-365}"
CURATED_MARKET_RETENTION_DAYS="${CURATED_MARKET_RETENTION_DAYS:-30}"
STATE_MACRO_RETENTION_DAYS="${STATE_MACRO_RETENTION_DAYS:-365}"
ANALYTICS_RETENTION_DAYS="${ANALYTICS_RETENTION_DAYS:-30}"
DLQ_MARKET_RETENTION_DAYS="${DLQ_MARKET_RETENTION_DAYS:-14}"
DLQ_MACRO_RETENTION_DAYS="${DLQ_MACRO_RETENTION_DAYS:-14}"

TOPICS=(
  "raw.market.finnhub.tick.v1:24:${RAW_MARKET_RETENTION_DAYS}:delete"
  "raw.macro.fred.release.v1:6:${RAW_MACRO_RETENTION_DAYS}:delete"
  "curated.market.bar.1m.v1:24:${CURATED_MARKET_RETENTION_DAYS}:delete"
  "state.macro.latest.v1:3:${STATE_MACRO_RETENTION_DAYS}:compact"
  "analytics.market_macro.1m.v1:12:${ANALYTICS_RETENTION_DAYS}:delete"
  "dlq.raw.market.finnhub.tick.v1:6:${DLQ_MARKET_RETENTION_DAYS}:delete"
  "dlq.raw.macro.fred.release.v1:3:${DLQ_MACRO_RETENTION_DAYS}:delete"
)

for item in "${TOPICS[@]}"; do
  IFS=":" read -r topic partitions retention_days cleanup_policy <<<"${item}"
  retention_ms=$((retention_days * 24 * 60 * 60 * 1000))
  docker compose exec -T kafka kafka-topics \
    --bootstrap-server kafka:9092 \
    --create \
    --if-not-exists \
    --topic "${topic}" \
    --partitions "${partitions}" \
    --replication-factor 1

  docker compose exec -T kafka kafka-configs \
    --bootstrap-server kafka:9092 \
    --entity-type topics \
    --entity-name "${topic}" \
    --alter \
    --add-config "retention.ms=${retention_ms},cleanup.policy=${cleanup_policy}"
done

echo "Kafka topics are ready."
