#!/usr/bin/env bash
set -euo pipefail

DRUID_API_URL="${DRUID_API_URL:-http://localhost:8888}"
DRUID_KAFKA_BOOTSTRAP_SERVERS="${DRUID_KAFKA_BOOTSTRAP_SERVERS:-kafka:9094}"
SPEC_TEMPLATE="05_serving/01_druid_specs/01_market_bar_1m_kafka.json.tmpl"

rendered_spec="$(mktemp)"
cleanup() {
  rm -f "${rendered_spec}"
}
trap cleanup EXIT

python3 - <<'PY' "${SPEC_TEMPLATE}" "${rendered_spec}" "${DRUID_KAFKA_BOOTSTRAP_SERVERS}"
from pathlib import Path
import sys

template_path = Path(sys.argv[1])
output_path = Path(sys.argv[2])
bootstrap_servers = sys.argv[3]

content = template_path.read_text(encoding="utf-8")
content = content.replace("__KAFKA_BOOTSTRAP_SERVERS__", bootstrap_servers)
output_path.write_text(content, encoding="utf-8")
PY

curl -sS -X POST \
  -H "Content-Type: application/json" \
  -d @"${rendered_spec}" \
  "${DRUID_API_URL}/druid/indexer/v1/supervisor"
