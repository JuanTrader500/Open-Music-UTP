"""Contratos Pydantic del módulo playlists (RF-013 a RF-015, RN-010)."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.catalog.schemas import ArtistOut, GenreOut


class PlaylistNameIn(BaseModel):
    """Body `{name}` para crear o renombrar una playlist."""

    name: str = Field(min_length=1, max_length=200)


class PlaylistTrackAdd(BaseModel):
    """Body para agregar una canción, con confirmación de duplicados."""

    track_id: str = Field(min_length=1, max_length=32)
    confirm_duplicate: bool = False


class PlaylistReorder(BaseModel):
    """Body con los identificadores actuales de la playlist en el nuevo orden."""

    playlist_track_ids: list[int] = Field(default_factory=list)


class PlaylistSummary(BaseModel):
    """Playlist en el listado del usuario."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    track_count: int
    created_at: datetime


class PlaylistTrackOut(BaseModel):
    """Canción dentro de una playlist, con su posición y su id de pertenencia."""

    playlist_track_id: int
    position: int
    track_id: str
    title: str
    artist: ArtistOut
    genre: GenreOut
    duration_s: int
    view_count: int
    like_count: int
    thumbnail_url: str
    is_embeddable: bool


class PlaylistDetail(BaseModel):
    """Detalle de una playlist con sus pistas ordenadas."""

    id: uuid.UUID
    name: str
    created_at: datetime
    tracks: list[PlaylistTrackOut] = Field(default_factory=list)
    total: int


class PlaylistListResponse(BaseModel):
    """Listado de playlists del usuario autenticado."""

    items: list[PlaylistSummary] = Field(default_factory=list)
    total: int
