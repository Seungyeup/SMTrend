#!/usr/bin/env bash
set -euo pipefail

TOPICS=(
  "raw.market.finnhub.tick.v1:24:7:delete"
  "raw.macro.fred.release.v1:6:365:delete"
  "curated.market.bar.1m.v1:24:30:delete"
  "state.macro.latest.v1:3:365:compact"
  "analytics.market_macro.1m.v1:12:30:delete"
  "dlq.raw.market.finnhub.tick.v1:6:14:delete"
  "dlq.raw.macro.fred.release.v1:3:14:delete"
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
