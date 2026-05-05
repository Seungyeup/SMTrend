#!/usr/bin/env bash
set -euo pipefail

python_bin="${PYTHON_BIN:-python}"
if [[ -x ".venv/bin/python" ]]; then
  python_bin=".venv/bin/python"
fi

"${python_bin}" -m poc_ingestion.main \
  --bootstrap-servers "${KAFKA_BOOTSTRAP_SERVERS:-localhost:9092}" \
  market-finnhub-poll \
  --symbol GOOG \
  --count 120 \
  --interval-s 2
