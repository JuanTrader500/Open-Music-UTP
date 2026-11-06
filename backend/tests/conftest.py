"""Configuración común de las pruebas.

Las pruebas de integración usan una base de datos dedicada (`*_test`) y nunca
la base de desarrollo. Las variables de entorno se fijan antes de importar
`app.main`, porque la configuración se construye al importar el módulo.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest
from dotenv import dotenv_values
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session

_DEFAULT_TEST_DATABASE_URL = "postgresql+psycopg://postgres:postgres@localhost:5433/openmusic_test"


def _resolve_test_database_url() -> str:
    """Prioriza TEST_DATABASE_URL y, si falta, deriva la base `_test` del `.env`."""
    explicit = os.environ.get("TEST_DATABASE_URL")
    if explicit:
        return explicit

    env_file = Path(__file__).resolve().parents[2] / ".env"
    file_values = dotenv_values(env_file) if env_file.exists() else {}
    base_url = os.environ.get("DATABASE_URL") or file_values.get("DATABASE_URL")
    if not base_url:
        return _DEFAULT_TEST_DATABASE_URL

    prefix, separator, database = base_url.rpartition("/")
    if not separator or not database:
        return _DEFAULT_TEST_DATABASE_URL
    database_name, query_separator, query = database.partition("?")
    if database_name.endswith("_test"):
        return base_url
    test_database = f"{database_name}_test"
    if query_separator:
        test_database = f"{test_database}?{query}"
    return f"{prefix}/{test_database}"


# La URL de pruebas se puede cambiar con TEST_DATABASE_URL (por ejemplo, otro
# puerto local). Si no se define, se deriva del DATABASE_URL local y se cambia
# el nombre de la base por uno terminado en `_test`.
TEST_DATABASE_URL = _resolve_test_database_url()

# Guarda de seguridad: el fixture borra y recrea tablas, así que la base debe
# ser explícitamente de pruebas.
_database_name = make_url(TEST_DATABASE_URL).database or ""
if not _database_name.endswith("_test"):
    raise RuntimeError(
        "TEST_DATABASE_URL debe apuntar a una base terminada en '_test' "
        "para no borrar datos de desarrollo."
    )

os.environ["DATABASE_URL"] = TEST_DATABASE_URL
os.environ.setdefault("JWT_SECRET", "clave-de-prueba-de-40-caracteres-1234567890")
os.environ.setdefault("MUSIC_PROVIDER", "simulated")
os.environ.setdefault("CORS_ORIGINS", "http://localhost:8080")

# Importar todos los modelos antes de crear las tablas de prueba.
import app.auth.models  # noqa: E402, F401
import app.catalog.models  # noqa: E402, F401
import app.favorites.models  # noqa: E402, F401
import app.listening.models  # noqa: E402, F401
import app.playlists.models  # noqa: E402, F401
import app.recommendations.models  # noqa: E402, F401
from app.core.base import Base  # noqa: E402
from app.core.database import get_db  # noqa: E402
from app.core.security import login_rate_limiter  # noqa: E402
from app.main import app  # noqa: E402


@pytest.fixture(scope="session")
def test_engine():
    """Crea el esquema una vez en la base de pruebas y lo elimina al final."""
    engine = create_engine(TEST_DATABASE_URL, pool_pre_ping=True)
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    try:
        yield engine
    finally:
        Base.metadata.drop_all(engine)
        engine.dispose()


@pytest.fixture
def db_session(test_engine):
    """Sesión dentro de una transacción que se revierte al terminar la prueba."""
    connection = test_engine.connect()
    transaction = connection.begin()
    session = Session(
        bind=connection,
        join_transaction_mode="create_savepoint",
        expire_on_commit=False,
    )
    try:
        yield session
    finally:
        session.close()
        transaction.rollback()
        connection.close()


@pytest.fixture
def client(db_session):
    """Cliente HTTP con la dependencia de base de datos apuntando a la prueba."""
    app.dependency_overrides[get_db] = lambda: db_session
    login_rate_limiter.clear()
    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        login_rate_limiter.clear()
        app.dependency_overrides.clear()
