"""Contratos Pydantic del catálogo (RF-010, RF-011, RF-012)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class GenreOut(BaseModel):
    """Género de la lista cerrada del SRS."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    code: str
    name: str


class ArtistOut(BaseModel):
    """Artista del catálogo global."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str


class TrackOut(BaseModel):
    """Canción con sus referencias de artista y género.

    No expone el JSON crudo del proveedor ni modelos ORM: el servicio arma este
    contrato a partir de las entidades persistidas.
    """

    track_id: str
    title: str
    artist: ArtistOut
    genre: GenreOut
    duration_s: int
    view_count: int
    like_count: int
    thumbnail_url: str
    is_embeddable: bool


class SearchResponse(BaseModel):
    """Resultado de una búsqueda de catálogo (RF-010)."""

    items: list[TrackOut] = Field(default_factory=list)
    total: int
    query: str


class ArtistListResponse(BaseModel):
    """Listado paginado de artistas (RF-021)."""

    items: list[ArtistOut] = Field(default_factory=list)
    total: int
    limit: int
    offset: int
