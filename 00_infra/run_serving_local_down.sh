#!/usr/bin/env bash
set -euo pipefail

docker compose \
  -f 00_infra/docker-compose.yaml \
  -f 00_infra/docker-compose.druid.yaml \
  --profile druid \
  stop druid-router druid-middlemanager druid-historical druid-broker druid-coordinator druid-zookeeper druid-postgres

docker compose \
  -f 00_infra/docker-compose.yaml \
  -f 00_infra/docker-compose.druid.yaml \
  --profile druid \
  rm -f druid-router druid-middlemanager druid-historical druid-broker druid-coordinator druid-zookeeper druid-postgres
