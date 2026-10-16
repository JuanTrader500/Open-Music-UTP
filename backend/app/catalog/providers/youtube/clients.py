"""Productos concretos de la familia YouTube (Data API v3).

Costos de cuota (SRS 1.3.4): search.list = 100 unidades, videos.list = 1.
"""
from __future__ import annotations

import json
from collections.abc import Sequence
from typing import Any

import httplib2
from googleapiclient.errors import HttpError

from app.catalog.providers.base import (
    PlaylistClient,
    SearchClient,
    VideoDetailsClient,
    validate_query,
)
from app.catalog.providers.models import TrackMetadata
from app.catalog.providers.youtube.mappers import map_video_item
from app.core.config import Settings
from app.core.exceptions import ProviderError, QuotaExceededError

_QUOTA_REASONS = {"quotaExceeded", "dailyLimitExceeded", "rateLimitExceeded"}
_MAX_BATCH = 50  # máximo de ids por llamada a videos.list


def _error_reason(exc: HttpError) -> str | None:
    try:
        payload = json.loads(exc.content.decode("utf-8"))
        return payload["error"]["errors"][0]["reason"]
    except (ValueError, KeyError, IndexError, TypeError, AttributeError):
        return None


def execute_request(request: Any) -> dict[str, Any]:
    """Ejecuta una petición y traduce los errores de YouTube a excepciones del dominio."""
    try:
        return request.execute()
    except HttpError as exc:
        status = getattr(exc.resp, "status", None)
        reason = _error_reason(exc)
        if status == 403 and reason in _QUOTA_REASONS:
            raise QuotaExceededError("Cuota diaria de YouTube agotada.") from exc
        raise ProviderError(f"Error de YouTube (HTTP {status}, motivo: {reason}).") from exc
    except (OSError, httplib2.HttpLib2Error) as exc:
        raise ProviderError("No fue posible contactar a YouTube.") from exc


class YouTubeSearchClient(SearchClient):
    """search.list restringido a música reproducible de forma embebida."""

    def __init__(self, resource: Any, settings: Settings) -> None:
        self._resource = resource
        self._settings = settings

    def search(self, query: str, max_results: int | None = None) -> list[str]:
        cleaned = validate_query(query)
        params: dict[str, Any] = {
            "part": "snippet",
            "q": cleaned,
            "type": "video",
            "videoCategoryId": self._settings.youtube_music_category_id,
            "videoEmbeddable": "true",
            "maxResults": max_results or self._settings.youtube_max_results,
        }
        if self._settings.youtube_region_code:
            params["regionCode"] = self._settings.youtube_region_code
        response = execute_request(self._resource.search().list(**params))
        return [item["id"]["videoId"] for item in response.get("items", [])]


class YouTubeVideoDetailsClient(VideoDetailsClient):
    """videos.list por lotes de hasta 50 ids (1 unidad de cuota por lote)."""

    def __init__(self, resource: Any) -> None:
        self._resource = resource

    def get_details(self, track_ids: Sequence[str]) -> list[TrackMetadata]:
        unique_ids = list(dict.fromkeys(track_ids))
        tracks: list[TrackMetadata] = []
        for start in range(0, len(unique_ids), _MAX_BATCH):
            chunk = unique_ids[start : start + _MAX_BATCH]
            request = self._resource.videos().list(
                part="snippet,contentDetails,statistics,status",
                id=",".join(chunk),
            )
            response = execute_request(request)
            tracks.extend(map_video_item(item) for item in response.get("items", []))
        return tracks


class YouTubePlaylistClient(PlaylistClient):
    """playlistItems.list con paginación, para las playlists semilla."""

    def __init__(self, resource: Any) -> None:
        self._resource = resource

    def list_track_ids(self, playlist_id: str, max_items: int = 50) -> list[str]:
        track_ids: list[str] = []
        page_token: str | None = None
        while len(track_ids) < max_items:
            params: dict[str, Any] = {
                "part": "contentDetails",
                "playlistId": playlist_id,
                "maxResults": min(50, max_items - len(track_ids)),
            }
            if page_token:
                params["pageToken"] = page_token
            response = execute_request(self._resource.playlistItems().list(**params))
            track_ids.extend(i["contentDetails"]["videoId"] for i in response.get("items", []))
            page_token = response.get("nextPageToken")
            if not page_token:
                break
        return track_ids[:max_items]
