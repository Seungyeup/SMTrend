#!/usr/bin/env bash
set -euo pipefail

python -m poc_ingestion.main \
  --bootstrap-servers "${KAFKA_BOOTSTRAP_SERVERS:-172.30.1.4:9092}" \
  fred-batch \
  --series DFF,CPIAUCSL,UNRATE \
  --limit 200
