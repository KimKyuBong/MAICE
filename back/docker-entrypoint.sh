#!/bin/sh
set -eu

# Run Alembic migrations before starting the app.
# - Uses DATABASE_URL via back/alembic/env.py (preferred over alembic.ini's sqlalchemy.url)
# - Retries to handle Postgres not being ready yet (depends_on does not wait for readiness)

MAX_RETRIES="${DB_MIGRATION_MAX_RETRIES:-60}"
SLEEP_SECONDS="${DB_MIGRATION_RETRY_SLEEP_SECONDS:-1}"

if [ "${AUTO_MIGRATE:-true}" = "true" ]; then
  echo "[entrypoint] AUTO_MIGRATE=true -> running: alembic upgrade head"
  i=1
  while [ "$i" -le "$MAX_RETRIES" ]; do
    if alembic upgrade head; then
      echo "[entrypoint] migrations applied successfully"
      break
    fi
    echo "[entrypoint] migration attempt ${i}/${MAX_RETRIES} failed; retrying in ${SLEEP_SECONDS}s..."
    i=$((i + 1))
    sleep "$SLEEP_SECONDS"
  done

  if [ "$i" -gt "$MAX_RETRIES" ]; then
    echo "[entrypoint] ERROR: migrations failed after ${MAX_RETRIES} attempts"
    exit 1
  fi
else
  echo "[entrypoint] AUTO_MIGRATE!=true -> skipping migrations"
fi

echo "[entrypoint] starting app: $*"
exec "$@"


