"""Base declarativa de SQLAlchemy y convenciones del esquema (RNF-015).

La convención de nombres replica la que PostgreSQL genera por defecto en el
esquema actual (`dataBase/schema.sql`), de modo que los modelos ORM y la base
de datos existente no diverjan cuando se ejecute `alembic check`.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, MetaData, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

#: Nombres equivalentes a los que produce PostgreSQL para el esquema v6.
NAMING_CONVENTION = {
    "ix": "%(table_name)s_%(column_0_name)s_idx",
    "uq": "%(table_name)s_%(column_0_name)s_key",
    "ck": "%(table_name)s_%(column_0_name)s_check",
    "fk": "%(table_name)s_%(column_0_name)s_fkey",
    "pk": "%(table_name)s_pkey",
}


class Base(DeclarativeBase):
    """Base declarativa común a todos los modelos del backend."""

    metadata = MetaData(naming_convention=NAMING_CONVENTION)


class CreatedAtMixin:
    """Columna `created_at` en UTC con valor por defecto del servidor."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class UpdatedAtMixin:
    """Columna `updated_at` en UTC con valor por defecto del servidor."""

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
