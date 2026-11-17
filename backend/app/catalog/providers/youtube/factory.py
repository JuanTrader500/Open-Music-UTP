"""Fábrica concreta: familia de clientes de YouTube."""

from __future__ import annotations

from typing import Any

from googleapiclient.discovery import build

from app.catalog.providers.base import (
    MusicProviderFactory,
    PlaylistClient,
    SearchClient,
    VideoDetailsClient,
)
from app.catalog.providers.youtube.adapter import YouTubeAdapter
from app.catalog.providers.youtube.clients import (
    YouTubePlaylistClient,
    YouTubeSearchClient,
    YouTubeVideoDetailsClient,
)
from app.core.config import Settings
from app.core.exceptions import ConfigurationError


class YouTubeProviderFactory(MusicProviderFactory):
    """Crea clientes de YouTube que comparten un único adaptador.

    El adaptador comparte el recurso `youtube v3` (misma clave y conexión) y
    es la única pieza que conoce `googleapiclient`.
    """

    name = "youtube"

    def __init__(self, settings: Settings, resource: Any | None = None) -> None:
        self._settings = settings
        self._resource = resource  # inyectable para pruebas
        self._adapter: YouTubeAdapter | None = None

    def _get_resource(self) -> Any:
        if self._resource is None:
            if not self._settings.youtube_api_key:
                raise ConfigurationError("Define YOUTUBE_API_KEY en el archivo .env.")
            self._resource = build(
                "youtube",
                "v3",
                developerKey=self._settings.youtube_api_key,
                cache_discovery=False,
            )
        return self._resource

    def _get_adapter(self) -> YouTubeAdapter:
        """Crea el adaptador una sola vez y lo comparte entre los tres clientes."""
        if self._adapter is None:
            self._adapter = YouTubeAdapter(self._get_resource(), self._settings)
        return self._adapter

    def create_search_client(self) -> SearchClient:
        return YouTubeSearchClient(self._get_adapter(), self._settings)

    def create_video_details_client(self) -> VideoDetailsClient:
        return YouTubeVideoDetailsClient(self._get_adapter())

    def create_playlist_client(self) -> PlaylistClient:
        return YouTubePlaylistClient(self._get_adapter())
