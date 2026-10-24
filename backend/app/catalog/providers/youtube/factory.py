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
from app.catalog.providers.youtube.clients import (
    YouTubePlaylistClient,
    YouTubeSearchClient,
    YouTubeVideoDetailsClient,
)
from app.core.config import Settings
from app.core.exceptions import ConfigurationError


class YouTubeProviderFactory(MusicProviderFactory):
    """Crea clientes de YouTube que comparten un único recurso `youtube v3`.

    Compartir el recurso es lo que hace "compatible" a la familia: los tres
    productos usan la misma clave y la misma conexión.
    """

    name = "youtube"

    def __init__(self, settings: Settings, resource: Any | None = None) -> None:
        self._settings = settings
        self._resource = resource  # inyectable para pruebas

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

    def create_search_client(self) -> SearchClient:
        return YouTubeSearchClient(self._get_resource(), self._settings)

    def create_video_details_client(self) -> VideoDetailsClient:
        return YouTubeVideoDetailsClient(self._get_resource())

    def create_playlist_client(self) -> PlaylistClient:
        return YouTubePlaylistClient(self._get_resource())
