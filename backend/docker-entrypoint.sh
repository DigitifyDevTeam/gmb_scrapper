#!/bin/sh
set -e

echo "Waiting for MySQL..."
python - <<'PY'
import socket
import sys
import time

host = "mysql"
port = 3306

for attempt in range(60):
    try:
        with socket.create_connection((host, port), timeout=2):
            print("MySQL is reachable.")
            sys.exit(0)
    except OSError:
        time.sleep(2)

print("MySQL did not become reachable in time.", file=sys.stderr)
sys.exit(1)
PY

echo "Running database migrations..."
alembic upgrade head

echo "Starting API server..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000
