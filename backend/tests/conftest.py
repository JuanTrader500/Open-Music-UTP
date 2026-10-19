"""Configuración común de las pruebas.

Define variables de entorno de prueba antes de importar `app.main`, para que
la aplicación pueda construirse sin secretos reales.
"""

from __future__ import annotations

import os

os.environ.setdefault("JWT_SECRET", "clave-de-prueba-de-40-caracteres-1234567890")
os.environ.setdefault("MUSIC_PROVIDER", "simulated")
os.environ.setdefault(
    "DATABASE_URL",
    "postgresql+psycopg://postgres:postgres@localhost:5433/openmusic",
)
