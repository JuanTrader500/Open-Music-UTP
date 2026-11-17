"""Resolución del género de una canción (RF-011, RN-009).

Prioridad: semilla > artista > categoría del proveedor > sin clasificar. La
función pura `resolve_genre` permite probar la regla sin base de datos; el
servicio se encarga de obtener los identificadores de cada fuente.
"""

from __future__ import annotations

from dataclasses import dataclass

#: Código del género comodín que no entra en recomendaciones por género (RN-009).
UNCLASSIFIED_CODE = "sin_clasificar"


@dataclass(frozen=True)
class GenreResolution:
    """Género elegido y la fuente que lo justifica."""

    genre_id: int
    source: str


def normalize_artist_name(name: str) -> str:
    """Normaliza el nombre del artista como lo exige el esquema v6."""
    return name.strip().lower()


def resolve_genre(
    *,
    seed_genre_id: int | None,
    artist_genre_id: int | None,
    category_genre_id: int | None,
    unclassified_genre_id: int,
) -> GenreResolution:
    """Aplica la prioridad de fuentes de género de RF-011."""
    if seed_genre_id is not None:
        return GenreResolution(genre_id=seed_genre_id, source="seed")
    if artist_genre_id is not None:
        return GenreResolution(genre_id=artist_genre_id, source="artist")
    if category_genre_id is not None:
        return GenreResolution(genre_id=category_genre_id, source="youtube_category")
    return GenreResolution(genre_id=unclassified_genre_id, source="unclassified")
