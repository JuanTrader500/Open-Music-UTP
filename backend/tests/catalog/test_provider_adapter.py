"""Pruebas del Adapter del proveedor de YouTube (entrega 2).

El recurso de YouTube se sustituye por un doble de prueba: estas pruebas nunca
llaman a la API real ni consumen cuota. Demuestran que el adaptador traduce la
interfaz externa a tipos del dominio y que los clientes ya no conocen el SDK.
"""

from __future__ import annotations

import ast
from pathlib import Path
from typing import Any

import httplib2
import pytest
from googleapiclient.errors import HttpError

from app.catalog.providers.models import TrackMetadata
from app.catalog.providers.youtube.adapter import YouTubeAdapter
from app.catalog.providers.youtube.clients import (
    YouTubePlaylistClient,
    YouTubeSearchClient,
    YouTubeVideoDetailsClient,
)
from app.catalog.providers.youtube.factory import YouTubeProviderFactory
from app.core.config import Settings
from app.core.exceptions import InvalidQueryError, ProviderError, QuotaExceededError

_CLIENTS_PATH = Path(__file__).resolve().parents[2] / "app/catalog/providers/youtube/clients.py"


# ------------------------------------- Dobles de prueba -------------------------------------
class _SuccessfulRequest:
    def __init__(self, payload: dict[str, Any]) -> None:
        self._payload = payload

    def execute(self) -> dict[str, Any]:
        return self._payload


class _FailingRequest:
    def __init__(self, error: Exception) -> None:
        self._error = error

    def execute(self) -> dict[str, Any]:
        raise self._error


class _FakeEndpoint:
    """Doble de `resource.search()`, `resource.videos()`, etc."""

    def __init__(self, *responses: dict[str, Any] | Exception) -> None:
        self._responses = list(responses)
        self.calls: list[dict[str, Any]] = []

    def list(self, **params: Any) -> _SuccessfulRequest | _FailingRequest:
        self.calls.append(params)
        response = self._responses.pop(0) if self._responses else {}
        if isinstance(response, Exception):
            return _FailingRequest(response)
        return _SuccessfulRequest(response)


class _FakeYouTubeResource:
    def __init__(
        self,
        *,
        search: _FakeEndpoint | None = None,
        videos: _FakeEndpoint | None = None,
        playlist_items: _FakeEndpoint | None = None,
    ) -> None:
        self.search_endpoint = search or _FakeEndpoint()
        self.videos_endpoint = videos or _FakeEndpoint()
        self.playlist_endpoint = playlist_items or _FakeEndpoint()

    def search(self) -> _FakeEndpoint:
        return self.search_endpoint

    def videos(self) -> _FakeEndpoint:
        return self.videos_endpoint

    def playlistItems(self) -> _FakeEndpoint:
        return self.playlist_endpoint


class _RecordingAdapter:
    """Adaptador falso para comprobar que los clientes solo delegan."""

    def __init__(self) -> None:
        self.search_calls: list[tuple[str, int | None]] = []
        self.detail_calls: list[list[str]] = []
        self.playlist_calls: list[tuple[str, int]] = []

    def search_video_ids(self, query: str, max_results: int | None = None) -> list[str]:
        self.search_calls.append((query, max_results))
        return ["x"]

    def get_video_details(self, track_ids: list[str]) -> list[TrackMetadata]:
        self.detail_calls.append(list(track_ids))
        return []

    def list_playlist_video_ids(self, playlist_id: str, max_items: int = 50) -> list[str]:
        self.playlist_calls.append((playlist_id, max_items))
        return []


def _video_item(track_id: str, *, embeddable: bool = True) -> dict[str, Any]:
    return {
        "id": track_id,
        "snippet": {"title": f"Titulo {track_id}", "channelTitle": "Artista"},
        "contentDetails": {"duration": "PT3M"},
        "statistics": {"viewCount": "10"},
        "status": {"embeddable": embeddable},
    }


def _adapter(resource: _FakeYouTubeResource, settings: Settings | None = None) -> YouTubeAdapter:
    return YouTubeAdapter(resource, settings or Settings())


# --------------------------------------- Búsqueda -----------------------------------------
def test_adapter_search_returns_video_ids_in_order():
    resource = _FakeYouTubeResource(
        search=_FakeEndpoint({"items": [{"id": {"videoId": "b"}}, {"id": {"videoId": "a"}}]})
    )
    assert _adapter(resource).search_video_ids("rock", 5) == ["b", "a"]
    params = resource.search_endpoint.calls[0]
    assert params == {
        "part": "snippet",
        "q": "rock",
        "type": "video",
        "videoCategoryId": "10",
        "videoEmbeddable": "true",
        "maxResults": 5,
    }


def test_adapter_search_skips_items_without_video_id():
    resource = _FakeYouTubeResource(
        search=_FakeEndpoint(
            {
                "items": [
                    {"id": {"videoId": "b"}},
                    {"id": {"kind": "youtube#video"}},
                    {"id": None},
                    {},
                    {"id": {"videoId": "a"}},
                ]
            }
        )
    )

    assert _adapter(resource).search_video_ids("bad bunny", 12) == ["b", "a"]


def test_adapter_search_uses_settings_defaults_and_region():
    resource = _FakeYouTubeResource(search=_FakeEndpoint({"items": []}))
    settings = Settings(youtube_region_code="CO", youtube_max_results=7)
    _adapter(resource, settings).search_video_ids("salsa")
    params = resource.search_endpoint.calls[0]
    assert params["maxResults"] == 7
    assert params["regionCode"] == "CO"

    without_region = _FakeYouTubeResource(search=_FakeEndpoint({"items": []}))
    _adapter(without_region, Settings()).search_video_ids("salsa")
    assert "regionCode" not in without_region.search_endpoint.calls[0]


# --------------------------------------- Detalles -----------------------------------------
def test_adapter_details_return_domain_track_metadata():
    resource = _FakeYouTubeResource(
        videos=_FakeEndpoint({"items": [_video_item("a"), _video_item("b", embeddable=False)]})
    )
    tracks = _adapter(resource).get_video_details(["a", "a", "b"])

    assert [track.track_id for track in tracks] == ["a", "b"]
    assert all(isinstance(track, TrackMetadata) for track in tracks)
    assert tracks[0].duration_s == 180 and tracks[0].channel_title == "Artista"
    assert tracks[1].is_embeddable is False
    assert resource.videos_endpoint.calls == [
        {"part": "snippet,contentDetails,statistics,status", "id": "a,b"}
    ]


def test_adapter_details_split_batches_of_fifty_ids():
    resource = _FakeYouTubeResource(videos=_FakeEndpoint({"items": []}, {"items": []}))
    track_ids = [f"t{i}" for i in range(51)]

    _adapter(resource).get_video_details(track_ids)

    first, second = resource.videos_endpoint.calls
    assert first["id"].count(",") == 49
    assert second["id"] == "t50"


# --------------------------------------- Playlist -----------------------------------------
def test_adapter_playlist_paginates_until_max_items():
    resource = _FakeYouTubeResource(
        playlist_items=_FakeEndpoint(
            {
                "items": [{"contentDetails": {"videoId": "a"}}],
                "nextPageToken": "page-2",
            },
            {"items": [{"contentDetails": {"videoId": "b"}}]},
        )
    )

    assert _adapter(resource).list_playlist_video_ids("PL1", max_items=2) == ["a", "b"]
    first, second = resource.playlist_endpoint.calls
    assert first["playlistId"] == "PL1" and "pageToken" not in first
    assert second["pageToken"] == "page-2"


def test_adapter_playlist_truncates_to_max_items():
    resource = _FakeYouTubeResource(
        playlist_items=_FakeEndpoint(
            {
                "items": [
                    {"contentDetails": {"videoId": "a"}},
                    {"contentDetails": {"videoId": "b"}},
                ]
            }
        )
    )

    assert _adapter(resource).list_playlist_video_ids("PL1", max_items=1) == ["a"]


# --------------------------------- Traducción de errores -----------------------------------
def _http_error(status: int, body: bytes) -> HttpError:
    return HttpError(httplib2.Response({"status": str(status)}), body)


def test_adapter_translates_quota_error():
    quota = _http_error(403, b'{"error": {"errors": [{"reason": "quotaExceeded"}]}}')
    resource = _FakeYouTubeResource(search=_FakeEndpoint(quota))

    with pytest.raises(QuotaExceededError):
        _adapter(resource).search_video_ids("rock")


def test_adapter_translates_general_http_error():
    failure = _http_error(500, b'{"error": {"errors": [{"reason": "backendError"}]}}')
    resource = _FakeYouTubeResource(search=_FakeEndpoint(failure))

    with pytest.raises(ProviderError) as excinfo:
        _adapter(resource).search_video_ids("rock")
    assert not isinstance(excinfo.value, QuotaExceededError)


@pytest.mark.parametrize("error", [OSError("sin red"), httplib2.HttpLib2Error("sin red")])
def test_adapter_translates_network_error(error: Exception):
    resource = _FakeYouTubeResource(search=_FakeEndpoint(error))

    with pytest.raises(ProviderError):
        _adapter(resource).search_video_ids("rock")


# --------------------------------------- Clientes -----------------------------------------
def test_search_client_validates_and_delegates_to_adapter():
    adapter = _RecordingAdapter()
    client = YouTubeSearchClient(adapter, Settings(search_min_chars=3))

    assert client.search("  rock  ", 4) == ["x"]
    assert adapter.search_calls == [("rock", 4)]

    with pytest.raises(InvalidQueryError):
        client.search("ab")
    assert adapter.search_calls == [("rock", 4)]


def test_details_and_playlist_clients_delegate_to_adapter():
    adapter = _RecordingAdapter()
    YouTubeVideoDetailsClient(adapter).get_details(["a", "b"])
    YouTubePlaylistClient(adapter).list_track_ids("PL1", 10)

    assert adapter.detail_calls == [["a", "b"]]
    assert adapter.playlist_calls == [("PL1", 10)]


def test_clients_do_not_import_the_youtube_sdk_nor_mappers():
    tree = ast.parse(_CLIENTS_PATH.read_text(encoding="utf-8"), filename=str(_CLIENTS_PATH))
    modules: list[str] = []
    names: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            modules.append(node.module)
            names.extend(alias.name for alias in node.names)

    roots = {module.split(".")[0] for module in modules}
    assert roots.isdisjoint({"googleapiclient", "httplib2", "json"})
    assert "map_video_item" not in names
    assert not any(module.endswith("mappers") for module in modules)


def test_factory_shares_a_single_adapter_between_clients():
    factory = YouTubeProviderFactory(Settings(), resource=_FakeYouTubeResource())

    clients = [
        factory.create_search_client(),
        factory.create_video_details_client(),
        factory.create_playlist_client(),
    ]

    assert len({id(client._adapter) for client in clients}) == 1
