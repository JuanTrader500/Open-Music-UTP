"""Productos concretos de la familia simulada (sin red, deterministas)."""

from __future__ import annotations

from collections.abc import Sequence

from app.catalog.providers.base import (
    PlaylistClient,
    SearchClient,
    VideoDetailsClient,
    validate_query,
)
from app.catalog.providers.models import TrackMetadata
from app.catalog.providers.simulated.data import SIMULATED_PLAYLISTS, SIMULATED_TRACKS


class SimulatedCatalog:
    """Estado compartido por los tres productos simulados."""

    def __init__(self) -> None:
        self.tracks = {t.track_id: t for t in SIMULATED_TRACKS}
        self.playlists = dict(SIMULATED_PLAYLISTS)


class SimulatedSearchClient(SearchClient):
    def __init__(self, catalog: SimulatedCatalog, min_chars: int, default_max_results: int) -> None:
        self._catalog = catalog
        self._min_chars = min_chars
        self._default_max_results = default_max_results

    def search(self, query: str, max_results: int | None = None) -> list[str]:
        needle = validate_query(query, self._min_chars).lower()
        hits = [
            t.track_id
            for t in self._catalog.tracks.values()
            if needle in t.title.lower() or needle in t.channel_title.lower()
        ]
        return hits[: max_results or self._default_max_results]


class SimulatedVideoDetailsClient(VideoDetailsClient):
    def __init__(self, catalog: SimulatedCatalog) -> None:
        self._catalog = catalog

    def get_details(self, track_ids: Sequence[str]) -> list[TrackMetadata]:
        return [
            self._catalog.tracks[v] for v in dict.fromkeys(track_ids) if v in self._catalog.tracks
        ]


class SimulatedPlaylistClient(PlaylistClient):
    def __init__(self, catalog: SimulatedCatalog) -> None:
        self._catalog = catalog

    def list_track_ids(self, playlist_id: str, max_items: int = 50) -> list[str]:
        return self._catalog.playlists.get(playlist_id, [])[:max_items]
