"""Modelos ORM del catálogo global (RF-010, RF-011, RF-012).

Reflejan las tablas `genres`, `artists`, `tracks` y `genre_seeds` del esquema
v6. No incluyen relaciones ORM cruzadas para mantener el desacoplamiento entre
módulos.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Identity,
    Index,
    SmallInteger,
    String,
    desc,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.base import Base


class Genre(Base):
    """Género de la lista cerrada (RF-011, RN-009)."""

    __tablename__ = "genres"

    id: Mapped[int] = mapped_column(SmallInteger, Identity(always=True), primary_key=True)
    code: Mapped[str] = mapped_column(String(30), nullable=False, unique=True)
    name: Mapped[str] = mapped_column(String(60), nullable=False)


class Artist(Base):
    """Artista de una canción; el nombre normalizado evita duplicados."""

    __tablename__ = "artists"

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    name_normalized: Mapped[str] = mapped_column(String(200), nullable=False, unique=True)


class Track(Base):
    """Canción del catálogo; `track_id` es el id del video (RF-010)."""

    __tablename__ = "tracks"

    track_id: Mapped[str] = mapped_column(String(32), primary_key=True)
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    artist_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("artists.id", ondelete="RESTRICT"),
        nullable=False,
    )
    genre_id: Mapped[int] = mapped_column(
        SmallInteger,
        ForeignKey("genres.id", ondelete="RESTRICT"),
        nullable=False,
    )
    genre_source: Mapped[str] = mapped_column(String(20), nullable=False)
    duration_s: Mapped[int] = mapped_column(nullable=False)
    view_count: Mapped[int] = mapped_column(BigInteger, nullable=False, server_default=text("0"))
    like_count: Mapped[int] = mapped_column(BigInteger, nullable=False, server_default=text("0"))
    thumbnail_url: Mapped[str] = mapped_column(String(2048), nullable=False)
    is_embeddable: Mapped[bool] = mapped_column(nullable=False, server_default=text("true"))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    __table_args__ = (
        CheckConstraint(
            "genre_source IN ('seed', 'artist', 'youtube_category', 'unclassified')",
            name="tracks_genre_source_check",
        ),
        CheckConstraint("duration_s >= 0", name="tracks_duration_s_check"),
        CheckConstraint("view_count >= 0", name="tracks_view_count_check"),
        CheckConstraint("like_count >= 0", name="tracks_like_count_check"),
        Index(
            "ix_tracks_genre_views",
            "genre_id",
            desc("view_count"),
            postgresql_where=text("is_embeddable"),
        ),
        Index(
            "ix_tracks_views",
            desc("view_count"),
            postgresql_where=text("is_embeddable"),
        ),
        Index("ix_tracks_artist", "artist_id"),
        Index("ix_tracks_genre_artist", "genre_id", "artist_id"),
    )


class GenreSeed(Base):
    """Playlist semilla de YouTube asociada a un género (RF-011)."""

    __tablename__ = "genre_seeds"

    playlist_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    genre_id: Mapped[int] = mapped_column(
        SmallInteger,
        ForeignKey("genres.id", ondelete="RESTRICT"),
        nullable=False,
    )
