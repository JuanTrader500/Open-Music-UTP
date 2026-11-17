"""Proxy de caché y cuota del catálogo (patrón Proxy, entrega 2).

Envuelve un `MusicProviderPort` por composición y mantiene la misma interfaz:
`CatalogService` no sabe que hay una caché delante. Solo se cachea
`search_tracks`; `import_playlist` pasa directo porque es una importación de
semillas y no una búsqueda de usuario.

La caché es de proceso, con TTL y expulsión LRU. Si YouTube agota la cuota, el
proxy devuelve la entrada vencida **de la misma clave** para no romper una
búsqueda que ya tenía resultado; para otra consulta propaga el error
(RF-010, RNF-024).
"""

from __future__ import annotations

import logging
import threading
import time
from collections import OrderedDict
from collections.abc import Callable
from dataclasses import dataclass

from app.catalog.providers.models import TrackMetadata
from app.catalog.providers.port import MusicProviderPort
from app.core.config import Settings
from app.core.exceptions import QuotaExceededError

logger = logging.getLogger(__name__)

_CacheKey = tuple[str, int]


@dataclass(frozen=True)
class _CacheEntry:
    """Resultado cacheado y momento en que deja de ser fresco."""

    tracks: tuple[TrackMetadata, ...]
    expires_at: float


class CachedMusicProvider:
    """Proxy que evita búsquedas repetidas y protege la cuota de YouTube."""

    def __init__(
        self,
        provider: MusicProviderPort,
        settings: Settings,
        *,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        """Recibe el proveedor real, la configuración y un reloj inyectable."""
        self._provider = provider
        self._ttl_s = settings.catalog_cache_ttl_s
        self._max_entries = settings.catalog_cache_max_entries
        self._default_max_results = settings.youtube_max_results
        self._clock = clock
        self._lock = threading.Lock()
        self._entries: OrderedDict[_CacheKey, _CacheEntry] = OrderedDict()

    def search_tracks(self, query: str, max_results: int | None = None) -> list[TrackMetadata]:
        """Devuelve la copia cacheada o consulta al proveedor y guarda el resultado."""
        key = (query.strip(), self._normalize_max_results(max_results))
        fresh = self._get_fresh(key, self._clock())
        if fresh is not None:
            logger.info("catalog cache=hit query=%r max_results=%d", key[0], key[1])
            return fresh

        logger.info("catalog cache=miss query=%r max_results=%d", key[0], key[1])
        try:
            tracks = self._provider.search_tracks(key[0], key[1])
        except QuotaExceededError:
            stale = self._get_stale(key, self._clock())
            if stale is not None:
                logger.info("catalog cache=stale query=%r max_results=%d", key[0], key[1])
                return stale
            raise

        self._store(key, tracks, self._clock())
        return list(tracks)

    def import_playlist(self, playlist_id: str, max_items: int = 50) -> list[TrackMetadata]:
        """Pasa directo: importar semillas no es una búsqueda de usuario."""
        return self._provider.import_playlist(playlist_id, max_items)

    def _normalize_max_results(self, max_results: int | None) -> int:
        """Normaliza `None` al máximo configurado para que la clave sea estable."""
        return self._default_max_results if max_results is None else max_results

    def _get_fresh(self, key: _CacheKey, now: float) -> list[TrackMetadata] | None:
        """Devuelve una copia si la entrada existe y no está vencida (LRU)."""
        with self._lock:
            entry = self._entries.get(key)
            if entry is None or entry.expires_at <= now:
                return None
            self._entries.move_to_end(key)
            return list(entry.tracks)

    def _get_stale(self, key: _CacheKey, now: float) -> list[TrackMetadata] | None:
        """Devuelve una copia de la entrada vencida de la misma clave, si existe."""
        with self._lock:
            entry = self._entries.get(key)
            if entry is None or entry.expires_at > now:
                return None
            self._entries.move_to_end(key)
            return list(entry.tracks)

    def _store(self, key: _CacheKey, tracks: list[TrackMetadata], now: float) -> None:
        """Guarda el resultado y expulsa la entrada menos usada si supera el máximo."""
        with self._lock:
            self._entries[key] = _CacheEntry(tuple(tracks), now + self._ttl_s)
            self._entries.move_to_end(key)
            while len(self._entries) > self._max_entries:
                self._entries.popitem(last=False)
