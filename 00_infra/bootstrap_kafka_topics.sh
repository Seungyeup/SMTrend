#!/usr/bin/env bash
set -euo pipefail

KAFKA_CONTAINER="${KAFKA_CONTAINER:-smtrend-kafka}"
KAFKA_BOOTSTRAP_SERVERS="${KAFKA_BOOTSTRAP_SERVERS:-localhost:9092}"

RAW_MARKET_RETENTION_DAYS="${RAW_MARKET_RETENTION_DAYS:-7}"
RAW_MACRO_RETENTION_DAYS="${RAW_MACRO_RETENTION_DAYS:-365}"
CURATED_MARKET_RETENTION_DAYS="${CURATED_MARKET_RETENTION_DAYS:-30}"
STATE_MACRO_RETENTION_DAYS="${STATE_MACRO_RETENTION_DAYS:-365}"
ANALYTICS_RETENTION_DAYS="${ANALYTICS_RETENTION_DAYS:-30}"

TOPICS=(
  "raw.market.finnhub.tick.v1:24:${RAW_MARKET_RETENTION_DAYS}:delete"
  "raw.macro.fred.release.v1:6:${RAW_MACRO_RETENTION_DAYS}:delete"
  "curated.market.bar.1m.v1:24:${CURATED_MARKET_RETENTION_DAYS}:delete"
  "state.macro.latest.v1:3:${STATE_MACRO_RETENTION_DAYS}:compact"
  "analytics.market_macro.1m.v1:12:${ANALYTICS_RETENTION_DAYS}:delete"
)

for item in "${TOPICS[@]}"; do
  IFS=":" read -r topic partitions retention_days cleanup_policy <<<"${item}"
  retention_ms=$((retention_days * 24 * 60 * 60 * 1000))

  docker exec "${KAFKA_CONTAINER}" /opt/kafka/bin/kafka-topics.sh \
    --bootstrap-server "${KAFKA_BOOTSTRAP_SERVERS}" \
    --create \
    --if-not-exists \
    --topic "${topic}" \
    --partitions "${partitions}" \
    --replication-factor 1

  docker exec "${KAFKA_CONTAINER}" /opt/kafka/bin/kafka-configs.sh \
    --bootstrap-server "${KAFKA_BOOTSTRAP_SERVERS}" \
    --entity-type topics \
    --entity-name "${topic}" \
    --alter \
    --add-config "retention.ms=${retention_ms},cleanup.policy=${cleanup_policy}"
done

echo "Kafka topics are ready on ${KAFKA_BOOTSTRAP_SERVERS}."
