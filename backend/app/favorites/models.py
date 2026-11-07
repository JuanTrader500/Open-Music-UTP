"""Modelo ORM de favoritos (RF-016)."""

from __future__ import annotations

import uuid

from sqlalchemy import ForeignKey, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.core.base import Base


class Favorite(Base):
    """Par único (usuario, canción) marcado como favorito."""

    __tablename__ = "favorites"

    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
    )
    track_id: Mapped[str] = mapped_column(
        String(32),
        ForeignKey("tracks.track_id", ondelete="RESTRICT"),
        primary_key=True,
    )
