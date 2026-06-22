#!/bin/sh
set -e

echo "Waiting for MySQL..."
python - <<'PY'
import asyncio
import sys
import time

import asyncmy


async def wait_for_mysql() -> None:
    host = "mysql"
    port = 3306
    user = "leadforge"
    password = "leadforge"
    database = "leadforge"
    max_attempts = 90

    for attempt in range(1, max_attempts + 1):
        try:
            conn = await asyncmy.connect(
                host=host,
                port=port,
                user=user,
                password=password,
                db=database,
                connect_timeout=3,
            )
            try:
                async with conn.cursor() as cursor:
                    await cursor.execute("SELECT 1")
            finally:
                conn.close()
            print("MySQL is ready.")
            return
        except Exception as exc:
            print(f"MySQL not ready ({attempt}/{max_attempts}): {exc}", flush=True)
            await asyncio.sleep(2)

    print("MySQL did not become ready in time.", file=sys.stderr)
    sys.exit(1)


asyncio.run(wait_for_mysql())
PY

echo "Running database migrations..."
alembic upgrade head

echo "Starting API server..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000
