#!/usr/bin/env bash
set -euo pipefail

python -m poc_ingestion.main \
  --bootstrap-servers "${KAFKA_BOOTSTRAP_SERVERS:-localhost:19092}" \
  market-mock \
  --symbol GOOG \
  --count 120 \
  --interval-s 1
