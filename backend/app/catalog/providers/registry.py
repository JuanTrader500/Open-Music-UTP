"""Selecciona la fábrica concreta según `MUSIC_PROVIDER` y crea el proveedor.

`get_music_provider` devuelve una única instancia por proceso: la caché del
proxy solo sirve si sobrevive entre peticiones (RNF-024). `reset_music_provider`
existe para que las pruebas limpien ese estado.
"""

from __future__ import annotations

from collections.abc import Callable
from threading import Lock

from app.catalog.providers.base import MusicProviderFactory
from app.catalog.providers.cached_provider import CachedMusicProvider
from app.catalog.providers.music_provider import MusicProvider
from app.catalog.providers.port import MusicProviderPort
from app.catalog.providers.simulated.factory import SimulatedProviderFactory
from app.catalog.providers.youtube.factory import YouTubeProviderFactory
from app.core.config import Settings
from app.core.exceptions import ConfigurationError

_FACTORIES: dict[str, Callable[[Settings], MusicProviderFactory]] = {
    YouTubeProviderFactory.name: YouTubeProviderFactory,
    SimulatedProviderFactory.name: SimulatedProviderFactory,
}

_music_provider: MusicProviderPort | None = None
_provider_lock = Lock()


def build_provider_factory(settings: Settings) -> MusicProviderFactory:
    """Devuelve la fábrica concreta del proveedor configurado."""
    try:
        return _FACTORIES[settings.music_provider](settings)
    except KeyError as exc:
        raise ConfigurationError(f"Proveedor desconocido: {settings.music_provider}") from exc


def build_music_provider(settings: Settings) -> MusicProviderPort:
    """Crea el proveedor configurado envuelto en el proxy de caché."""
    return CachedMusicProvider(MusicProvider(build_provider_factory(settings)), settings)


def get_music_provider(settings: Settings) -> MusicProviderPort:
    """Devuelve el proveedor del proceso y lo crea la primera vez que se pide."""
    global _music_provider
    with _provider_lock:
        if _music_provider is None:
            _music_provider = build_music_provider(settings)
        return _music_provider


def reset_music_provider() -> None:
    """Descarta la instancia compartida; se usa entre pruebas."""
    global _music_provider
    with _provider_lock:
        _music_provider = None
