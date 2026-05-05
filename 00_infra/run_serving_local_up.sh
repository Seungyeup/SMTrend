#!/usr/bin/env bash
set -euo pipefail

docker compose \
  -f 00_infra/docker-compose.yaml \
  -f 00_infra/docker-compose.druid.yaml \
  --profile druid \
  up -d druid-postgres druid-zookeeper druid-coordinator druid-broker druid-historical druid-middlemanager druid-router
