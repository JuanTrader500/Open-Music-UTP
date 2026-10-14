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
        self.tracks = {t.video_id: t for t in SIMULATED_TRACKS}
        self.playlists = dict(SIMULATED_PLAYLISTS)


class SimulatedSearchClient(SearchClient):
    def __init__(self, catalog: SimulatedCatalog) -> None:
        self._catalog = catalog

    def search(self, query: str, max_results: int | None = None) -> list[str]:
        needle = validate_query(query).lower()
        hits = [
            t.video_id
            for t in self._catalog.tracks.values()
            if needle in t.title.lower() or needle in t.channel_title.lower()
        ]
        return hits[: max_results or 20]


class SimulatedVideoDetailsClient(VideoDetailsClient):
    def __init__(self, catalog: SimulatedCatalog) -> None:
        self._catalog = catalog

    def get_details(self, video_ids: Sequence[str]) -> list[TrackMetadata]:
        return [self._catalog.tracks[v] for v in dict.fromkeys(video_ids) if v in self._catalog.tracks]


class SimulatedPlaylistClient(PlaylistClient):
    def __init__(self, catalog: SimulatedCatalog) -> None:
        self._catalog = catalog

    def list_video_ids(self, playlist_id: str, max_items: int = 50) -> list[str]:
        return self._catalog.playlists.get(playlist_id, [])[:max_items]
