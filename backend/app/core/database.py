"""Conexión a PostgreSQL y sesión de SQLAlchemy (RNF-015, RNF-016).

`get_db` entrega una sesión por petición, revierte ante cualquier error y
siempre la cierra; nunca hace `commit`, que es responsabilidad del servicio.
"""

from __future__ import annotations

from collections.abc import Iterator
from functools import lru_cache

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings


@lru_cache
def get_engine() -> Engine:
    """Crea (una sola vez) el motor de base de datos a partir de la configuración."""
    return create_engine(
        get_settings().database_url,
        pool_pre_ping=True,
        pool_size=5,
        max_overflow=10,
    )


SessionLocal = sessionmaker(autoflush=False, expire_on_commit=False)


def get_db() -> Iterator[Session]:
    """Dependencia que entrega una sesión de base de datos por petición."""
    session = SessionLocal(bind=get_engine())
    try:
        yield session
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
