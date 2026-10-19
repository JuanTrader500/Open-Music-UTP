"""Pruebas de la configuración central (`app/core/config.py`)."""

from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from app.core import config
from app.core.config import Settings
from app.core.exceptions import ConfigurationError

VALID_URL = "postgresql+psycopg://postgres:postgres@localhost:5433/openmusic"
ENV_EXAMPLE = Path(__file__).resolve().parents[3] / ".env.example"


def _settings(**overrides) -> Settings:
    """Crea una configuración con valores válidos y los cambios indicados."""
    base = {"database_url": VALID_URL, "jwt_secret": "a" * 32, "music_provider": "simulated"}
    base.update(overrides)
    return Settings(**base)


def test_valores_por_defecto():
    settings = Settings()
    assert settings.music_provider == "simulated"
    assert settings.youtube_max_results == 20
    assert settings.log_level == "INFO"
    assert settings.database_url == ""
    assert settings.jwt_secret == ""
    assert settings.access_token_expire_minutes == 60
    assert settings.cors_origins == "http://localhost:8080"
    assert settings.login_attempts_per_minute == 5
    assert settings.password_min_length == 8
    assert settings.previous_track_threshold_s == 5
    assert settings.skipped_threshold_s == 30
    assert settings.max_playlists_per_user == 50
    assert settings.max_tracks_per_playlist == 500
    assert settings.playlist_name_max_length == 80
    assert settings.search_min_chars == 2
    assert settings.onboarding_min_genres == 3
    assert settings.onboarding_max_genres == 5
    assert settings.genre_initial_weight_min == 10.0
    assert settings.artist_initial_weight_min == 5.0
    assert settings.preference_halving_minutes == 120
    assert settings.recency_half_life_days == 14
    assert settings.recommendations_list_size == 20
    assert settings.exploration_share == 0.30


def test_from_env_lee_y_convierte(monkeypatch):
    monkeypatch.setattr(config, "load_dotenv", lambda: None)
    monkeypatch.setenv("MUSIC_PROVIDER", "youtube")
    monkeypatch.setenv("ACCESS_TOKEN_EXPIRE_MINUTES", "15")
    monkeypatch.setenv("EXPLORATION_SHARE", "0.5")

    settings = Settings.from_env()

    assert settings.music_provider == "youtube"
    assert settings.access_token_expire_minutes == 15
    assert isinstance(settings.access_token_expire_minutes, int)
    assert settings.exploration_share == 0.5
    assert isinstance(settings.exploration_share, float)


def test_from_env_ignora_variable_vacia(monkeypatch):
    monkeypatch.setattr(config, "load_dotenv", lambda: None)
    monkeypatch.setenv("MUSIC_PROVIDER", "")

    assert Settings.from_env().music_provider == "simulated"


def test_cors_origins_list_separa_y_limpia():
    settings = Settings(cors_origins="http://localhost:8080, https://app.example.com ,")
    assert settings.cors_origins_list == ["http://localhost:8080", "https://app.example.com"]


def test_password_min_length_invalido():
    with pytest.raises(ValidationError):
        Settings(password_min_length=7)


def test_playlist_name_max_length_invalido():
    with pytest.raises(ValidationError):
        Settings(playlist_name_max_length=81)


def test_onboarding_rango_invalido():
    with pytest.raises(ValidationError):
        Settings(onboarding_min_genres=6, onboarding_max_genres=5)


def test_validate_runtime_jwt_corto():
    with pytest.raises(ConfigurationError):
        _settings(jwt_secret="a" * 31).validate_runtime()


def test_validate_runtime_url_invalida():
    with pytest.raises(ConfigurationError):
        _settings(
            database_url="postgresql://usuario:clave@localhost:5432/openmusic"
        ).validate_runtime()


def test_validate_runtime_youtube_sin_clave():
    with pytest.raises(ConfigurationError):
        _settings(music_provider="youtube", youtube_api_key="").validate_runtime()


def test_validate_runtime_valida():
    _settings().validate_runtime()


def test_env_example_cubre_todos_los_campos():
    # Cada campo de Settings debe tener su variable en .env.example (misma
    # convención que from_env: nombre.upper()); si no, la configuración se
    # desincroniza en silencio. Se aceptan líneas comentadas (campos opcionales).
    claves = set()
    for linea in ENV_EXAMPLE.read_text(encoding="utf-8").splitlines():
        texto = linea.lstrip("#").strip()
        if "=" in texto:
            claves.add(texto.split("=", 1)[0].strip())

    faltantes = [name.upper() for name in Settings.model_fields if name.upper() not in claves]
    assert faltantes == []
