"""Modelos ORM de preferencias del onboarding (RF-021, RN-007)."""

from __future__ import annotations

import uuid
from decimal import Decimal

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    ForeignKey,
    Numeric,
    SmallInteger,
    Uuid,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.base import Base


class UserGenrePreference(Base):
    """Género elegido en el onboarding y su peso inicial."""

    __tablename__ = "user_genre_preferences"

    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
    )
    genre_id: Mapped[int] = mapped_column(
        SmallInteger,
        ForeignKey("genres.id", ondelete="CASCADE"),
        primary_key=True,
    )
    initial_weight: Mapped[Decimal] = mapped_column(
        Numeric(6, 2), nullable=False, server_default=text("10")
    )

    __table_args__ = (
        CheckConstraint(
            "initial_weight > 0",
            name="user_genre_preferences_initial_weight_check",
        ),
    )


class UserArtistPreference(Base):
    """Artista elegido en el onboarding y su peso inicial."""

    __tablename__ = "user_artist_preferences"

    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
    )
    artist_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("artists.id", ondelete="CASCADE"),
        primary_key=True,
    )
    initial_weight: Mapped[Decimal] = mapped_column(
        Numeric(6, 2), nullable=False, server_default=text("5")
    )

    __table_args__ = (
        CheckConstraint(
            "initial_weight > 0",
            name="user_artist_preferences_initial_weight_check",
        ),
    )
