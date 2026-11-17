"""Adapter del SDK de YouTube (patrón Adapter, entrega 2).

El dominio no debe conocer `googleapiclient`: ni sus recursos, ni la forma de
construir peticiones, ni sus excepciones `HttpError`. Este adaptador convierte
esa interfaz externa incómoda en operaciones del proyecto que devuelven tipos
del dominio (`list[str]` y `list[TrackMetadata]`) y traduce los fallos del
proveedor a `QuotaExceededError` / `ProviderError`.

`mappers.py` es un detalle interno del adaptador: los clientes concretos ya no
parsean respuestas crudas de YouTube (RF-010, RF-011, RNF-003, RNF-023).
"""

from __future__ import annotations

import json
from collections.abc import Sequence
from typing import Any

import httplib2
from googleapiclient.errors import HttpError

from app.catalog.providers.models import TrackMetadata
from app.catalog.providers.youtube.mappers import map_video_item
from app.core.config import Settings
from app.core.exceptions import ProviderError, QuotaExceededError

_QUOTA_REASONS = {"quotaExceeded", "dailyLimitExceeded", "rateLimitExceeded"}
_MAX_BATCH = 50  # máximo de ids por llamada a videos.list


class YouTubeAdapter:
    """Envuelve el recurso `youtube v3` y expone operaciones del dominio.

    La fábrica de YouTube crea una sola instancia y la comparte entre los tres
    clientes, igual que antes compartía el recurso crudo.
    """

    def __init__(self, resource: Any, settings: Settings) -> None:
        self._resource = resource
        self._settings = settings

    # ------------------------------- Operaciones del dominio -------------------------------
    def search_video_ids(self, query: str, max_results: int | None = None) -> list[str]:
        """Busca videos musicales y devuelve sus identificadores en orden (RF-010).

        YouTube puede devolver resultados sin `id.videoId` (videos no disponibles,
        privados o ítems incompletos). El adaptador los descarta para que un
        resultado inválido no tumbe toda la búsqueda con un `KeyError`.
        """
        params: dict[str, Any] = {
            "part": "snippet",
            "q": query,
            "type": "video",
            "videoCategoryId": self._settings.youtube_music_category_id,
            "videoEmbeddable": "true",
            "maxResults": max_results or self._settings.youtube_max_results,
        }
        if self._settings.youtube_region_code:
            params["regionCode"] = self._settings.youtube_region_code
        response = self._execute(self._resource.search().list(**params))

        video_ids: list[str] = []
        for item in response.get("items", []):
            item_id = item.get("id") if isinstance(item, dict) else None
            video_id = item_id.get("videoId") if isinstance(item_id, dict) else None
            if video_id:
                video_ids.append(video_id)
        return video_ids

    def get_video_details(self, track_ids: Sequence[str]) -> list[TrackMetadata]:
        """Obtiene `TrackMetadata` por lotes de hasta 50 ids (1 unidad por lote)."""
        unique_ids = list(dict.fromkeys(track_ids))
        tracks: list[TrackMetadata] = []
        for start in range(0, len(unique_ids), _MAX_BATCH):
            chunk = unique_ids[start : start + _MAX_BATCH]
            request = self._resource.videos().list(
                part="snippet,contentDetails,statistics,status",
                id=",".join(chunk),
            )
            response = self._execute(request)
            tracks.extend(map_video_item(item) for item in response.get("items", []))
        return tracks

    def list_playlist_video_ids(self, playlist_id: str, max_items: int = 50) -> list[str]:
        """Lee los identificadores de una playlist semilla con paginación (RF-011)."""
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
            response = self._execute(self._resource.playlistItems().list(**params))
            track_ids.extend(i["contentDetails"]["videoId"] for i in response.get("items", []))
            page_token = response.get("nextPageToken")
            if not page_token:
                break
        return track_ids[:max_items]

    # ----------------------------------- Infraestructura -----------------------------------
    def _execute(self, request: Any) -> dict[str, Any]:
        """Ejecuta una petición y traduce los errores de YouTube al dominio."""
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


def _error_reason(exc: HttpError) -> str | None:
    """Extrae el motivo de error del cuerpo JSON de YouTube, si está disponible."""
    try:
        payload = json.loads(exc.content.decode("utf-8"))
        return payload["error"]["errors"][0]["reason"]
    except (ValueError, KeyError, IndexError, TypeError, AttributeError):
        return None
