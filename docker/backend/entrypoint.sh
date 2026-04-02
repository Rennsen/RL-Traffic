#!/usr/bin/env bash
set -euo pipefail

mkdir -p /app/data /app/artifacts

if find /app/alembic/versions -mindepth 1 -type f | read -r _; then
  alembic upgrade head
fi

exec uvicorn app.main:app --host 0.0.0.0 --port 8000
