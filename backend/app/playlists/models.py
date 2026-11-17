"""Modelos ORM de playlists y sus pistas (RF-013 a RF-015, RN-010)."""

from __future__ import annotations

import uuid

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    ForeignKey,
    Identity,
    Index,
    Integer,
    String,
    UniqueConstraint,
    Uuid,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.base import Base, CreatedAtMixin


class Playlist(Base, CreatedAtMixin):
    """Playlist de un usuario registrado (RF-013)."""

    __tablename__ = "playlists"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(80), nullable=False)

    __table_args__ = (
        CheckConstraint("length(btrim(name)) >= 1", name="playlists_name_check"),
        Index("ix_playlists_user", "user_id"),
    )


class PlaylistTrack(Base):
    """Pista dentro de una playlist, con posición ordenable (RF-014, RF-015)."""

    __tablename__ = "playlist_tracks"

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    playlist_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("playlists.id", ondelete="CASCADE"),
        nullable=False,
    )
    track_id: Mapped[str] = mapped_column(
        String(32),
        ForeignKey("tracks.track_id", ondelete="RESTRICT"),
        nullable=False,
    )
    position: Mapped[int] = mapped_column(Integer, nullable=False)

    __table_args__ = (
        CheckConstraint("position >= 1", name="playlist_tracks_position_check"),
        UniqueConstraint(
            "playlist_id",
            "position",
            name="playlist_tracks_playlist_id_position_key",
            deferrable=True,
            initially="DEFERRED",
        ),
    )
