"""Entorno de Alembic para Open Music UTP.

La URL de la base de datos se toma de la configuración por entorno, no de
`alembic.ini`. Todos los modelos se importan aquí para que autogenerate vea el
esquema completo.
"""

from __future__ import annotations

from alembic import context
from sqlalchemy import engine_from_config, pool

import app.auth.models  # noqa: F401
import app.catalog.models  # noqa: F401
import app.favorites.models  # noqa: F401
import app.listening.models  # noqa: F401
import app.playlists.models  # noqa: F401
import app.recommendations.models  # noqa: F401
from app.core.base import Base
from app.core.config import get_settings

config = context.config
# `ConfigParser` interpola `%`; se escapa para admitir contraseñas URL-encoded.
config.set_main_option("sqlalchemy.url", get_settings().database_url.replace("%", "%%"))

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Ejecuta las migraciones sin conexión, generando SQL."""
    context.configure(
        url=config.get_main_option("sqlalchemy.url"),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        compare_server_default=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Ejecuta las migraciones contra una conexión real."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
            compare_server_default=True,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
