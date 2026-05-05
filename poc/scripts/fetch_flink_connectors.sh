#!/usr/bin/env bash
set -euo pipefail

mkdir -p flink/lib
curl -fL \
  -o flink/lib/flink-sql-connector-kafka-3.1.0-1.18.jar \
  "https://repo1.maven.org/maven2/org/apache/flink/flink-sql-connector-kafka/3.1.0-1.18/flink-sql-connector-kafka-3.1.0-1.18.jar"

curl -fL \
  -o flink/lib/flink-connector-kafka-3.1.0-1.18.jar \
  "https://repo1.maven.org/maven2/org/apache/flink/flink-connector-kafka/3.1.0-1.18/flink-connector-kafka-3.1.0-1.18.jar"

curl -fL \
  -o flink/lib/kafka-clients-3.4.0.jar \
  "https://repo1.maven.org/maven2/org/apache/kafka/kafka-clients/3.4.0/kafka-clients-3.4.0.jar"

echo "Flink Kafka connector jars downloaded to flink/lib/."
