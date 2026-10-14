"""Fábrica concreta: familia de clientes simulados (para pruebas y demos sin cuota)."""
from __future__ import annotations

from app.catalog.providers.base import (
    MusicProviderFactory,
    PlaylistClient,
    SearchClient,
    VideoDetailsClient,
)
from app.catalog.providers.simulated.clients import (
    SimulatedCatalog,
    SimulatedPlaylistClient,
    SimulatedSearchClient,
    SimulatedVideoDetailsClient,
)
from app.core.config import Settings


class SimulatedProviderFactory(MusicProviderFactory):
    name = "simulated"

    def __init__(self, settings: Settings | None = None) -> None:
        self._catalog = SimulatedCatalog()

    def create_search_client(self) -> SearchClient:
        return SimulatedSearchClient(self._catalog)

    def create_video_details_client(self) -> VideoDetailsClient:
        return SimulatedVideoDetailsClient(self._catalog)

    def create_playlist_client(self) -> PlaylistClient:
        return SimulatedPlaylistClient(self._catalog)
