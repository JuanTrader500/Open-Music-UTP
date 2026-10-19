"""Selecciona la fábrica concreta según `MUSIC_PROVIDER`."""

from __future__ import annotations

from collections.abc import Callable

from app.catalog.providers.base import MusicProviderFactory
from app.catalog.providers.simulated.factory import SimulatedProviderFactory
from app.catalog.providers.youtube.factory import YouTubeProviderFactory
from app.core.config import Settings
from app.core.exceptions import ConfigurationError

_FACTORIES: dict[str, Callable[[Settings], MusicProviderFactory]] = {
    YouTubeProviderFactory.name: YouTubeProviderFactory,
    SimulatedProviderFactory.name: SimulatedProviderFactory,
}


def build_provider_factory(settings: Settings) -> MusicProviderFactory:
    try:
        return _FACTORIES[settings.music_provider](settings)
    except KeyError as exc:
        raise ConfigurationError(f"Proveedor desconocido: {settings.music_provider}") from exc
