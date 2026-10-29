"""Código cliente del Abstract Factory.

`MusicProvider` recibe una `MusicProviderFactory` ABSTRACTA: no sabe si detrás
hay YouTube o datos simulados. Orquesta el flujo búsqueda -> detalles (RF-010)
y la importación de playlists semilla (RF-011).
"""

from __future__ import annotations

from app.catalog.providers.base import MusicProviderFactory
from app.catalog.providers.models import TrackMetadata


class MusicProvider:
    def __init__(self, factory: MusicProviderFactory) -> None:
        self._search = factory.create_search_client()
        self._details = factory.create_video_details_client()
        self._playlists = factory.create_playlist_client()

    def search_tracks(self, query: str, max_results: int | None = None) -> list[TrackMetadata]:
        """Busca, trae detalles y descarta no embebibles (RN-012)."""
        track_ids = self._search.search(query, max_results)
        return self._hydrate(track_ids)

    def import_playlist(self, playlist_id: str, max_items: int = 50) -> list[TrackMetadata]:
        """Lee una playlist semilla y devuelve sus canciones reproducibles."""
        track_ids = self._playlists.list_track_ids(playlist_id, max_items)
        return self._hydrate(track_ids)

    def _hydrate(self, track_ids: list[str]) -> list[TrackMetadata]:
        if not track_ids:
            return []
        by_id = {t.track_id: t for t in self._details.get_details(track_ids)}
        ordered = [by_id[v] for v in track_ids if v in by_id]  # conserva el orden de origen
        return [t for t in ordered if t.is_embeddable]
