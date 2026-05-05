#!/usr/bin/env bash
set -euo pipefail

docker compose -f 06_visualization/superset/docker-compose.yaml up -d
