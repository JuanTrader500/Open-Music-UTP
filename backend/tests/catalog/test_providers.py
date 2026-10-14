from unittest.mock import MagicMock

import httplib2
import pytest
from googleapiclient.errors import HttpError

from app.catalog.providers.base import MusicProviderFactory
from app.catalog.providers.music_provider import MusicProvider
from app.catalog.providers.registry import build_provider_factory
from app.catalog.providers.simulated.factory import SimulatedProviderFactory
from app.catalog.providers.youtube.factory import YouTubeProviderFactory
from app.catalog.providers.youtube.mappers import map_video_item, parse_iso8601_duration
from app.core.config import Settings
from app.core.exceptions import (
    ConfigurationError,
    InvalidQueryError,
    QuotaExceededError,
)


def test_parse_duration():
    assert parse_iso8601_duration("PT3M45S") == 225
    assert parse_iso8601_duration("PT1H2M3S") == 3723
    assert parse_iso8601_duration("PT45S") == 45
    assert parse_iso8601_duration("basura") == 0


def test_registry_returns_abstract_factory_subtypes():
    sim = build_provider_factory(Settings(music_provider="simulated"))
    yt = build_provider_factory(Settings(music_provider="youtube"))
    assert isinstance(sim, MusicProviderFactory) and isinstance(sim, SimulatedProviderFactory)
    assert isinstance(yt, MusicProviderFactory) and isinstance(yt, YouTubeProviderFactory)


def test_simulated_flow_filters_non_embeddable_and_keeps_order():
    provider = MusicProvider(SimulatedProviderFactory())
    assert [t.video_id for t in provider.search_tracks("cafeteros")] == ["sim_rock_01", "sim_rock_02"]
    salsa = provider.import_playlist("PL_SIM_SALSA")
    assert [t.video_id for t in salsa] == ["sim_salsa_01", "sim_salsa_02"]  # sin la no embebible


def test_short_query_is_rejected_without_calling_provider():
    resource = MagicMock()
    provider = MusicProvider(YouTubeProviderFactory(Settings(), resource=resource))
    with pytest.raises(InvalidQueryError):
        provider.search_tracks("a")
    resource.search.assert_not_called()


def test_youtube_family_with_fake_resource():
    resource = MagicMock()
    resource.search.return_value.list.return_value.execute.return_value = {
        "items": [{"id": {"videoId": "b"}}, {"id": {"videoId": "a"}}]
    }
    resource.videos.return_value.list.return_value.execute.return_value = {
        "items": [
            {"id": "a", "snippet": {"title": "A", "channelTitle": "Art", "thumbnails": {"high": {"url": "u"}}},
             "contentDetails": {"duration": "PT3M"}, "statistics": {"viewCount": "10"},
             "status": {"embeddable": True}},
            {"id": "b", "snippet": {"title": "B", "channelTitle": "Art"},
             "contentDetails": {"duration": "PT1M"}, "statistics": {}, "status": {"embeddable": True}},
        ]
    }
    provider = MusicProvider(YouTubeProviderFactory(Settings(), resource=resource))
    tracks = provider.search_tracks("rock")
    assert [t.video_id for t in tracks] == ["b", "a"]  # orden de search.list
    assert tracks[1].duration_s == 180 and tracks[1].thumbnail_url == "u"
    kwargs = resource.search.return_value.list.call_args.kwargs
    assert kwargs["videoCategoryId"] == "10" and kwargs["videoEmbeddable"] == "true"


def test_quota_error_is_translated():
    err = HttpError(
        httplib2.Response({"status": "403"}),
        b'{"error": {"errors": [{"reason": "quotaExceeded"}]}}',
    )
    resource = MagicMock()
    resource.search.return_value.list.return_value.execute.side_effect = err
    provider = MusicProvider(YouTubeProviderFactory(Settings(), resource=resource))
    with pytest.raises(QuotaExceededError):
        provider.search_tracks("rock")


def test_missing_api_key_raises_configuration_error():
    with pytest.raises(ConfigurationError):
        MusicProvider(YouTubeProviderFactory(Settings(youtube_api_key="")))


def test_map_video_item_hidden_likes():
    track = map_video_item({"id": "x", "snippet": {"title": "T"}, "statistics": {"viewCount": "5"}})
    assert track.like_count == 0 and track.is_embeddable is False
