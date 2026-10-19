"""Patrón Abstract Factory — interfaces (productos abstractos + fábrica abstracta).

Familia de productos relacionados que necesita el catálogo:
    * SearchClient        -> buscar canciones por texto      (YouTube: search.list)
    * VideoDetailsClient  -> detalles por lotes              (YouTube: videos.list)
    * PlaylistClient      -> leer playlists semilla          (YouTube: playlistItems.list)

`MusicProviderFactory` declara cómo crear la familia completa. Cada fábrica
concreta (YouTube, simulada) entrega productos que SÍ son compatibles entre sí.
El código cliente (`MusicProvider`) solo depende de estas abstracciones.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Sequence

from app.catalog.providers.models import TrackMetadata
from app.core.exceptions import InvalidQueryError


def validate_query(query: str, min_chars: int) -> str:
    """Valida y normaliza la consulta antes de gastar cuota (RF-010).

    `min_chars` llega desde la configuración (`search_min_chars`); así no hay
    constantes de negocio en el código.
    """
    cleaned = query.strip()
    if len(cleaned) < min_chars:
        raise InvalidQueryError(f"La búsqueda debe tener al menos {min_chars} caracteres.")
    return cleaned


# ----------------------------- Productos abstractos -----------------------------
class SearchClient(ABC):
    """Producto abstracto A: búsqueda de canciones."""

    @abstractmethod
    def search(self, query: str, max_results: int | None = None) -> list[str]:
        """Devuelve los `track_id` que coinciden con la consulta, en orden."""


class VideoDetailsClient(ABC):
    """Producto abstracto B: metadatos de canciones por lotes."""

    @abstractmethod
    def get_details(self, track_ids: Sequence[str]) -> list[TrackMetadata]:
        """Devuelve los metadatos de los `track_id` indicados."""


class PlaylistClient(ABC):
    """Producto abstracto C: lectura de playlists semilla."""

    @abstractmethod
    def list_track_ids(self, playlist_id: str, max_items: int = 50) -> list[str]:
        """Devuelve los `track_id` de una playlist, en orden."""


# ------------------------------- Fábrica abstracta --------------------------------
class MusicProviderFactory(ABC):
    """Fábrica abstracta: crea la familia completa de clientes de un proveedor."""

    #: nombre con el que se registra en `registry.py`
    name: str = "abstract"

    @abstractmethod
    def create_search_client(self) -> SearchClient: ...

    @abstractmethod
    def create_video_details_client(self) -> VideoDetailsClient: ...

    @abstractmethod
    def create_playlist_client(self) -> PlaylistClient: ...
