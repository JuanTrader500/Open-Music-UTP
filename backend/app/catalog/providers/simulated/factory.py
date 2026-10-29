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

    def __init__(self, settings: Settings) -> None:
        self._catalog = SimulatedCatalog()
        self._min_chars = settings.search_min_chars
        # El tope de resultados nuevo es `youtube_max_results` (RF-010); el
        # proveedor simulado respeta el mismo valor para no duplicar constantes.
        self._max_results = settings.youtube_max_results

    def create_search_client(self) -> SearchClient:
        return SimulatedSearchClient(self._catalog, self._min_chars, self._max_results)

    def create_video_details_client(self) -> VideoDetailsClient:
        return SimulatedVideoDetailsClient(self._catalog)

    def create_playlist_client(self) -> PlaylistClient:
        return SimulatedPlaylistClient(self._catalog)
