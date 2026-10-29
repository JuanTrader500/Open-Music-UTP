"""Modelos de datos (pydantic) que intercambia el proveedor con el resto del sistema.

Son independientes de YouTube: el resto de la app solo conoce estos modelos,
así un cambio en la API externa no se propaga (riesgo R-02).
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class TrackMetadata(BaseModel):
    """Una canción con los metadatos que exige el SRS (ver entidad `tracks`).

    Es inmutable a propósito: es un objeto de valor que solo se lee y se
    comparte entre capas, nunca se modifica in situ.
    """

    model_config = ConfigDict(frozen=True)

    track_id: str
    title: str
    channel_title: str  # se usa como "artista" (RF-010)
    duration_s: int = Field(ge=0)
    view_count: int = Field(default=0, ge=0)
    like_count: int = Field(default=0, ge=0)
    thumbnail_url: str | None = None
    is_embeddable: bool = True
