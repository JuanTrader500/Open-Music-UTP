#!/bin/sh
set -eu

# Un volumen creado con dataBase/schema.sql ya tiene tablas, pero no la tabla
# `alembic_version`. En ese caso marcamos el esquema actual como base antes de
# aplicar migraciones futuras. Una base vacía se crea con `alembic upgrade`.
if python - <<'PY'
import os
import sys

from sqlalchemy import create_engine, inspect

engine = create_engine(os.environ["DATABASE_URL"], pool_pre_ping=True)
tables = set(inspect(engine).get_table_names())
engine.dispose()
sys.exit(0 if "alembic_version" not in tables and "users" in tables else 1)
PY
then
    echo "Esquema existente sin alembic_version: marcando la revisión actual."
    alembic stamp head
fi

echo "Aplicando migraciones Alembic."
alembic upgrade head

# Los géneros y artistas base son necesarios incluso con YouTube: el servicio
# resuelve el género de cada canción contra esa lista cerrada.
python -m app.catalog.seed_importer --base-only

if [ "${SEED_CATALOG:-false}" = "true" ] && [ "${MUSIC_PROVIDER:-simulated}" = "simulated" ]; then
    echo "Importando playlists simuladas del catálogo."
    python -m app.catalog.seed_importer --all
fi

exec uvicorn app.main:app --host 0.0.0.0 --port 8000
