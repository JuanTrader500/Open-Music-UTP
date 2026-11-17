"""Puerto del proveedor de música (Proxy, entrega 2).

`MusicProviderPort` es la interfaz que consume `CatalogService`. Tanto el
proveedor real (`MusicProvider`) como el proxy de caché (`CachedMusicProvider`)
la cumplen, y el servicio no distingue uno de otro.
"""

from __future__ import annotations

from typing import Protocol

from app.catalog.providers.models import TrackMetadata


class MusicProviderPort(Protocol):
    """Operaciones del proveedor que necesita el catálogo (RF-010, RF-011)."""

    def search_tracks(self, query: str, max_results: int | None = None) -> list[TrackMetadata]:
        """Busca canciones y devuelve solo las reproducibles."""
        ...

    def import_playlist(self, playlist_id: str, max_items: int = 50) -> list[TrackMetadata]:
        """Lee una playlist semilla y devuelve sus canciones reproducibles."""
        ...
