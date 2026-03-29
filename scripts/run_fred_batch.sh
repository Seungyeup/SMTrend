#!/usr/bin/env bash
set -euo pipefail

python -m poc_ingestion.main \
  --bootstrap-servers "${KAFKA_BOOTSTRAP_SERVERS:-localhost:19092}" \
  fred-batch \
  --series DFF,CPIAUCSL,UNRATE \
  --limit 200
