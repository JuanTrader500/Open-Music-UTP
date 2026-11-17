"""Pruebas del Proxy de caché y cuota (entrega 2, RNF-024).

No hay red ni base de datos: el proveedor real se sustituye por un contador y
el reloj es inyectable, así que la expiración se prueba sin `sleep`.
"""

from __future__ import annotations

import logging
from types import SimpleNamespace

import pytest

from app.catalog.providers.cached_provider import CachedMusicProvider
from app.catalog.providers.models import TrackMetadata
from app.catalog.providers.registry import get_music_provider, reset_music_provider
from app.catalog.service import CatalogService
from app.core.config import Settings
from app.core.exceptions import QuotaExceededError


class _Clock:
    """Reloj controlado para probar el TTL sin esperas reales."""

    def __init__(self) -> None:
        self.now = 1_000.0

    def __call__(self) -> float:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += seconds


class _CountingProvider:
    """Proveedor falso que cuenta llamadas y puede simular cuota agotada."""

    def __init__(self, *, quota_after: int | None = None) -> None:
        self.search_calls: list[tuple[str, int | None]] = []
        self.playlist_calls: list[tuple[str, int]] = []
        self._quota_after = quota_after

    def search_tracks(self, query: str, max_results: int | None = None) -> list[TrackMetadata]:
        self.search_calls.append((query, max_results))
        if self._quota_after is not None and len(self.search_calls) > self._quota_after:
            raise QuotaExceededError("Cuota agotada para la prueba.")
        return [_track(f"t-{query}")]

    def import_playlist(self, playlist_id: str, max_items: int = 50) -> list[TrackMetadata]:
        self.playlist_calls.append((playlist_id, max_items))
        return [_track(f"seed-{playlist_id}")]


class _FakeRepository:
    """Repositorio mínimo para el flujo de `CatalogService.search`."""

    def get_or_create_artist(self, name: str) -> SimpleNamespace:
        return SimpleNamespace(id=1)

    def get_track(self, track_id: str) -> None:
        return None

    def get_artist_genre_id(self, artist_id: int) -> None:
        return None

    def get_genre_by_code(self, code: str) -> SimpleNamespace:
        return SimpleNamespace(id=1)

    def upsert_track(self, **values) -> SimpleNamespace:
        return SimpleNamespace(**values)

    def get_track_views(self, track_ids: list[str]) -> dict:
        return {}


class _FakeDb:
    """Sesión falsa para aislar el servicio del motor de base de datos."""

    def commit(self) -> None:
        pass

    def rollback(self) -> None:
        pass


def _track(track_id: str) -> TrackMetadata:
    return TrackMetadata(
        track_id=track_id,
        title=f"Título {track_id}",
        channel_title="Artista",
        duration_s=180,
    )


def _settings(**overrides) -> Settings:
    base = {
        "catalog_cache_ttl_s": 60,
        "catalog_cache_max_entries": 2,
        "youtube_max_results": 20,
    }
    base.update(overrides)
    return Settings(**base)


@pytest.fixture(autouse=True)
def _clean_registry():
    """Aísla el singleton de proveedor entre pruebas."""
    reset_music_provider()
    yield
    reset_music_provider()


@pytest.fixture
def clock() -> _Clock:
    return _Clock()


# ---------------------------------- Hit, miss y clave --------------------------------------
def test_identical_search_within_ttl_is_a_hit(clock):
    provider = _CountingProvider()
    cache = CachedMusicProvider(provider, _settings(), clock=clock)

    first = cache.search_tracks("  rock  ", 10)
    clock.advance(59)
    second = cache.search_tracks("rock", 10)

    assert provider.search_calls == [("rock", 10)]
    assert [t.track_id for t in second] == [t.track_id for t in first]
    assert first is not second  # cada hit entrega una copia de la lista


def test_different_query_is_a_miss(clock):
    provider = _CountingProvider()
    cache = CachedMusicProvider(provider, _settings(), clock=clock)

    cache.search_tracks("rock", 10)
    cache.search_tracks("pop", 10)

    assert provider.search_calls == [("rock", 10), ("pop", 10)]


def test_none_max_results_is_normalized_to_the_configured_default(clock):
    provider = _CountingProvider()
    cache = CachedMusicProvider(provider, _settings(youtube_max_results=20), clock=clock)

    cache.search_tracks("rock")
    cache.search_tracks("rock", 20)

    assert provider.search_calls == [("rock", 20)]


def test_expired_entry_triggers_a_new_call(clock):
    provider = _CountingProvider()
    cache = CachedMusicProvider(provider, _settings(catalog_cache_ttl_s=60), clock=clock)

    cache.search_tracks("rock", 10)
    clock.advance(61)
    cache.search_tracks("rock", 10)

    assert provider.search_calls == [("rock", 10), ("rock", 10)]


# --------------------------------------- LRU -----------------------------------------------
def test_lru_evicts_the_least_recently_used_entry(clock):
    provider = _CountingProvider()
    cache = CachedMusicProvider(provider, _settings(catalog_cache_max_entries=2), clock=clock)

    cache.search_tracks("a", 10)
    cache.search_tracks("b", 10)
    clock.advance(1)
    cache.search_tracks("a", 10)  # "a" pasa a ser la más reciente
    cache.search_tracks("c", 10)  # expulsa "b"
    cache.search_tracks("b", 10)  # vuelve a consultar el proveedor

    assert provider.search_calls == [
        ("a", 10),
        ("b", 10),
        ("c", 10),
        ("b", 10),
    ]


def test_cache_never_exceeds_the_configured_maximum(clock):
    provider = _CountingProvider()
    cache = CachedMusicProvider(provider, _settings(catalog_cache_max_entries=2), clock=clock)

    for query in ("a", "b", "c"):
        cache.search_tracks(query, 10)

    assert len(cache._entries) == 2


# ------------------------------- Cuota agotada y respaldo ----------------------------------
def test_quota_error_returns_stale_entry_for_the_same_key(clock):
    provider = _CountingProvider(quota_after=1)
    cache = CachedMusicProvider(provider, _settings(catalog_cache_ttl_s=60), clock=clock)

    cache.search_tracks("rock", 10)
    clock.advance(61)

    stale = cache.search_tracks("rock", 10)

    assert provider.search_calls == [("rock", 10), ("rock", 10)]
    assert [t.track_id for t in stale] == ["t-rock"]


def test_quota_error_with_a_different_key_is_propagated(clock):
    provider = _CountingProvider(quota_after=1)
    cache = CachedMusicProvider(provider, _settings(), clock=clock)

    cache.search_tracks("rock", 10)
    clock.advance(61)

    with pytest.raises(QuotaExceededError):
        cache.search_tracks("pop", 10)


def test_quota_error_without_a_cached_entry_is_propagated(clock):
    provider = _CountingProvider(quota_after=0)
    cache = CachedMusicProvider(provider, _settings(), clock=clock)

    with pytest.raises(QuotaExceededError):
        cache.search_tracks("rock", 10)


# --------------------------------- Importación de semillas --------------------------------
def test_import_playlist_is_not_cached(clock):
    provider = _CountingProvider()
    cache = CachedMusicProvider(provider, _settings(), clock=clock)

    cache.import_playlist("PL1", 10)
    cache.import_playlist("PL1", 10)

    assert provider.playlist_calls == [("PL1", 10), ("PL1", 10)]


# ------------------------------------- Registros ------------------------------------------
def test_logs_hit_miss_and_stale(clock, caplog):
    provider = _CountingProvider(quota_after=1)
    cache = CachedMusicProvider(provider, _settings(catalog_cache_ttl_s=60), clock=clock)

    with caplog.at_level(logging.INFO, logger="app.catalog.providers.cached_provider"):
        cache.search_tracks("rock", 10)  # miss
        cache.search_tracks("rock", 10)  # hit
        clock.advance(61)
        cache.search_tracks("rock", 10)  # quota -> stale

    assert "cache=miss" in caplog.text
    assert "cache=hit" in caplog.text
    assert "cache=stale" in caplog.text


# -------------------------------- Singleton y fachada -------------------------------------
def test_get_music_provider_is_a_process_singleton():
    settings = Settings(music_provider="simulated")

    first = get_music_provider(settings)
    assert get_music_provider(settings) is first

    reset_music_provider()
    second = get_music_provider(settings)

    assert first is not second
    assert isinstance(second, CachedMusicProvider)


def test_catalog_service_uses_the_shared_provider():
    settings = Settings(music_provider="simulated")

    first = CatalogService(_FakeDb(), settings, repository=_FakeRepository())
    second = CatalogService(_FakeDb(), settings, repository=_FakeRepository())

    assert first.provider is second.provider
    assert isinstance(first.provider, CachedMusicProvider)


def test_two_catalog_services_share_the_cache(clock):
    settings = _settings()
    provider = _CountingProvider()
    cache = CachedMusicProvider(provider, settings, clock=clock)
    first = CatalogService(_FakeDb(), settings, provider=cache, repository=_FakeRepository())
    second = CatalogService(_FakeDb(), settings, provider=cache, repository=_FakeRepository())

    first.search("rock", 10)
    second.search("rock", 10)

    assert provider.search_calls == [("rock", 10)]
