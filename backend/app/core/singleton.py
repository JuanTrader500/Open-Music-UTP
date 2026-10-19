"""Singleton transversal (RNF-031, ESC-05).

Garantiza una única instancia de la configuración / estado global en el proceso.
Se usa junto a `get_settings()` (lru_cache) en `core/config.py`.
"""

from __future__ import annotations


class SingletonMeta(type):
    """Metaclase Singleton: una sola instancia por clase."""

    _instances: dict[type, object] = {}

    def __call__(cls, *args, **kwargs):  # type: ignore[override]
        if cls not in cls._instances:
            cls._instances[cls] = super().__call__(*args, **kwargs)
        return cls._instances[cls]

    @classmethod
    def clear(mcs, cls: type | None = None) -> None:
        """Solo para tests: olvida instancias cacheadas."""
        if cls is None:
            mcs._instances.clear()
        else:
            mcs._instances.pop(cls, None)
