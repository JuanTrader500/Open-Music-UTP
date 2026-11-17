"""Productos concretos de la familia YouTube (Data API v3).

Los clientes solo conocen el adaptador (`YouTubeAdapter`): ya no importan el
SDK, no construyen peticiones ni leen JSON crudo del proveedor. Costos de cuota
(SRS 1.3.4): search.list = 100 unidades, videos.list = 1.
"""

from __future__ import annotations

from collections.abc import Sequence

from app.catalog.providers.base import (
    PlaylistClient,
    SearchClient,
    VideoDetailsClient,
    validate_query,
)
from app.catalog.providers.models import TrackMetadata
from app.catalog.providers.youtube.adapter import YouTubeAdapter
from app.core.config import Settings


class YouTubeSearchClient(SearchClient):
    """search.list restringido a música reproducible de forma embebida."""

    def __init__(self, adapter: YouTubeAdapter, settings: Settings) -> None:
        self._adapter = adapter
        self._settings = settings

    def search(self, query: str, max_results: int | None = None) -> list[str]:
        cleaned = validate_query(query, self._settings.search_min_chars)
        return self._adapter.search_video_ids(cleaned, max_results)


class YouTubeVideoDetailsClient(VideoDetailsClient):
    """videos.list por lotes de hasta 50 ids (1 unidad de cuota por lote)."""

    def __init__(self, adapter: YouTubeAdapter) -> None:
        self._adapter = adapter

    def get_details(self, track_ids: Sequence[str]) -> list[TrackMetadata]:
        return self._adapter.get_video_details(track_ids)


class YouTubePlaylistClient(PlaylistClient):
    """playlistItems.list con paginación, para las playlists semilla."""

    def __init__(self, adapter: YouTubeAdapter) -> None:
        self._adapter = adapter

    def list_track_ids(self, playlist_id: str, max_items: int = 50) -> list[str]:
        return self._adapter.list_playlist_video_ids(playlist_id, max_items)
