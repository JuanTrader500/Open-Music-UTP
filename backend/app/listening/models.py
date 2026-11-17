"""Modelo ORM de eventos de escucha (RF-023, RF-024, RN-005, RN-014)."""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Identity,
    Index,
    Integer,
    Numeric,
    String,
    Uuid,
    desc,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.base import Base


class ListeningEvent(Base):
    """Tiempo realmente escuchado de una pista por un usuario."""

    __tablename__ = "listening_events"

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    track_id: Mapped[str] = mapped_column(
        String(32),
        ForeignKey("tracks.track_id", ondelete="RESTRICT"),
        nullable=False,
    )
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    seconds_listened: Mapped[int] = mapped_column(Integer, nullable=False)
    duration_s: Mapped[int] = mapped_column(Integer, nullable=False)
    fraction_listened: Mapped[Decimal] = mapped_column(Numeric(5, 4), nullable=False)
    skipped: Mapped[bool] = mapped_column(Boolean, nullable=False)
    session_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    is_simulated: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("false")
    )

    __table_args__ = (
        CheckConstraint(
            "seconds_listened >= 0",
            name="listening_events_seconds_listened_check",
        ),
        CheckConstraint(
            "duration_s >= 0",
            name="listening_events_duration_s_check",
        ),
        CheckConstraint(
            "fraction_listened BETWEEN 0 AND 1",
            name="listening_events_fraction_listened_check",
        ),
        Index("ix_events_user_started", "user_id", desc("started_at")),
        Index("ix_events_user_track", "user_id", "track_id"),
    )
