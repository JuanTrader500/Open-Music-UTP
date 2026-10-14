"""Configuración central del backend (RNF-031: todo por variables de entorno).

Usa pydantic para validar y python-dotenv para leer el archivo .env.
Los parámetros configurables del SRS viven aquí y no en el código.
"""
from __future__ import annotations

import os
from functools import lru_cache
from typing import Literal

from dotenv import load_dotenv
from pydantic import BaseModel, Field


class Settings(BaseModel):
    """Configuración validada de la aplicación."""

    # Proveedor de música activo: define QUÉ fábrica concreta se usa.
    music_provider: Literal["youtube", "simulated"] = "youtube"

    # YouTube Data API v3 (RNF-003)
    youtube_api_key: str = ""
    youtube_max_results: int = Field(default=20, ge=1, le=50)  # RF-010: hasta 20
    youtube_music_category_id: str = "10"  # categoría "Music" de YouTube
    youtube_region_code: str | None = None

    @classmethod
    def from_env(cls) -> "Settings":
        load_dotenv()
        return cls(
            music_provider=os.getenv("MUSIC_PROVIDER", "youtube"),
            youtube_api_key=os.getenv("YOUTUBE_API_KEY", ""),
            youtube_max_results=int(os.getenv("YOUTUBE_MAX_RESULTS", "20")),
            youtube_music_category_id=os.getenv("YOUTUBE_MUSIC_CATEGORY_ID", "10"),
            youtube_region_code=os.getenv("YOUTUBE_REGION_CODE") or None,
        )


@lru_cache
def get_settings() -> Settings:
    return Settings.from_env()
