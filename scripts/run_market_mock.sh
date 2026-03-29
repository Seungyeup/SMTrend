#!/usr/bin/env bash
set -euo pipefail

python_bin="${PYTHON_BIN:-python}"
if [[ -x ".venv/bin/python" ]]; then
  python_bin=".venv/bin/python"
fi

"${python_bin}" -m poc_ingestion.main \
  --bootstrap-servers "${KAFKA_BOOTSTRAP_SERVERS:-localhost:19092}" \
  market-mock \
  --symbol "${MARKET_MOCK_SYMBOL:-GOOG}" \
  --count "${MARKET_MOCK_COUNT:-0}" \
  --interval-s "${MARKET_MOCK_INTERVAL_S:-1}" \
  --start-price "${MARKET_MOCK_START_PRICE:-180.0}"
