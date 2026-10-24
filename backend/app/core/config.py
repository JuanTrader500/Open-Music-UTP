"""Configuración central del backend, leída de variables de entorno.

Todos los parámetros configurables del SRS viven aquí y no en el código
(RNF-031). `Settings` no valida secretos al construirse, para que las pruebas
puedan crearla sin ellos; esa validación se hace en `validate_runtime()`, que
se ejecuta al arrancar la aplicación.
"""

from __future__ import annotations

import os
from functools import lru_cache
from typing import Literal

from dotenv import load_dotenv
from pydantic import BaseModel, Field, model_validator

from app.core.exceptions import ConfigurationError
from app.core.singleton import SingletonMeta


class Settings(BaseModel):
    """Configuración de la aplicación validada por pydantic."""

    # Proveedor de música activo: define qué fábrica concreta se usa.
    music_provider: Literal["youtube", "simulated"] = "simulated"

    # YouTube Data API v3 (RNF-003)
    youtube_api_key: str = ""
    youtube_max_results: int = Field(default=20, ge=1, le=50)  # RF-010
    youtube_music_category_id: str = "10"
    youtube_region_code: str | None = None

    # Registros (RNF-034)
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"

    # Base de datos (RNF-018)
    database_url: str = ""

    # Seguridad (RNF-027, RNF-029, RN-004)
    jwt_secret: str = ""
    access_token_expire_minutes: int = Field(default=60, ge=1)
    cors_origins: str = "http://localhost:8080"
    login_attempts_per_minute: int = Field(default=5, ge=1)
    password_min_length: int = Field(default=8, ge=8)

    # Reglas del SRS
    previous_track_threshold_s: int = Field(default=5, ge=0)  # RN-001
    skipped_threshold_s: int = Field(default=30, ge=0)  # RN-005
    max_playlists_per_user: int = Field(default=50, ge=1)  # RN-010
    max_tracks_per_playlist: int = Field(default=500, ge=1)  # RN-010
    playlist_name_max_length: int = Field(default=80, ge=1, le=80)  # RF-013
    search_min_chars: int = Field(default=2, ge=1)  # RF-010
    onboarding_min_genres: int = Field(default=3, ge=1)  # RF-021
    onboarding_max_genres: int = Field(default=5, ge=1)  # RF-021
    genre_initial_weight_min: float = Field(default=10.0, gt=0)  # RN-007
    artist_initial_weight_min: float = Field(default=5.0, gt=0)  # RN-007
    preference_halving_minutes: int = Field(default=120, ge=1)  # RN-007
    recency_half_life_days: int = Field(default=14, ge=1)  # RN-006
    recommendations_list_size: int = Field(default=20, ge=1)  # RF-026
    exploration_share: float = Field(default=0.30, ge=0, le=1)  # RF-026

    @classmethod
    def from_env(cls) -> Settings:
        """Crea la configuración leyendo `.env` y las variables de entorno.

        Solo se pasan las variables presentes y no vacías; pydantic convierte
        los textos a los tipos declarados.
        """
        load_dotenv()
        values = {
            name: os.environ[name.upper()]
            for name in cls.model_fields
            if os.environ.get(name.upper(), "") != ""
        }
        return cls(**values)

    @model_validator(mode="after")
    def _check_onboarding_range(self) -> Settings:
        """Comprueba que el mínimo de géneros no supere el máximo (RF-021)."""
        if self.onboarding_min_genres > self.onboarding_max_genres:
            raise ValueError("onboarding_min_genres no puede superar onboarding_max_genres")
        return self

    @property
    def cors_origins_list(self) -> list[str]:
        """Devuelve los orígenes CORS separados por comas y sin espacios (RNF-030)."""
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    def validate_runtime(self) -> None:
        """Valida la configuración obligatoria al arrancar; no expone valores."""
        problems: list[str] = []
        if not self.database_url.startswith("postgresql+psycopg://"):
            problems.append("DATABASE_URL")
        if len(self.jwt_secret) < 32:
            problems.append("JWT_SECRET (mínimo 32 caracteres)")
        if self.music_provider == "youtube" and not self.youtube_api_key:
            problems.append("YOUTUBE_API_KEY")
        if problems:
            raise ConfigurationError("Configuración inválida: " + ", ".join(problems))


@lru_cache
def get_settings() -> Settings:
    """Singleton funcional: devuelve la misma configuración en todo el proceso."""
    return Settings.from_env()


class AppRuntime(metaclass=SingletonMeta):
    """Singleton de objeto conservado como demostración del patrón (RNF-021).

    Ningún servicio ni router debe importarlo; la configuración se inyecta con
    `Depends(get_settings)`. Se mantiene para documentar el patrón Singleton.
    """

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings: Settings = settings or get_settings()

    def reload(self, settings: Settings) -> None:
        """Reemplaza la configuración en memoria."""
        self.settings = settings


def get_runtime(settings: Settings | None = None) -> AppRuntime:
    """Acceso global al runtime (Singleton); conservado solo como demostración."""
    runtime = AppRuntime()
    if settings is not None:
        runtime.reload(settings)
    return runtime
