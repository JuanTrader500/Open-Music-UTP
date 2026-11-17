"""Pruebas unitarias de seguridad: hash, JWT y rate limit (RNF-026/027/029)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import jwt
import pytest

from app.core.config import Settings
from app.core.exceptions import RateLimitedError, UnauthorizedError
from app.core.security import (
    LoginRateLimiter,
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)

SECRET = "clave-de-prueba-de-40-caracteres-1234567890"


def _settings() -> Settings:
    """Configuración mínima válida para probar tokens."""
    return Settings(
        database_url="postgresql+psycopg://postgres:postgres@localhost:5433/openmusic_test",
        jwt_secret=SECRET,
        music_provider="simulated",
        access_token_expire_minutes=60,
    )


def test_hash_y_verificacion_de_password():
    password = "Clave-segura-123"
    password_hash = hash_password(password)

    assert password_hash != password
    assert verify_password(password, password_hash) is True
    assert verify_password("otra-clave", password_hash) is False


def test_hash_usa_sal_aleatoria():
    password = "Clave-segura-123"

    assert hash_password(password) != hash_password(password)


def test_verificar_hash_invalido_no_lanza_error():
    assert verify_password("Clave-segura-123", "esto-no-es-un-hash") is False


def test_token_ida_y_vuelta():
    user_id = "2f1c8d1e-5e5a-4f7e-9d5a-123456789abc"

    token = create_access_token(user_id, _settings())

    assert decode_access_token(token, _settings()) == user_id


def test_token_expirado_es_rechazado():
    settings = _settings()
    issued_at = datetime.now(UTC) - timedelta(minutes=settings.access_token_expire_minutes + 1)

    token = create_access_token("usuario", settings, now=issued_at)

    with pytest.raises(UnauthorizedError):
        decode_access_token(token, settings)


def test_token_con_firma_incorrecta_es_rechazado():
    token = create_access_token("usuario", _settings())
    other_settings = _settings()
    other_settings.jwt_secret = "otra-clave-de-40-caracteres-123456789"

    with pytest.raises(UnauthorizedError):
        decode_access_token(token, other_settings)


def test_token_sin_sub_es_rechazado():
    settings = _settings()
    token = jwt.encode({"exp": int(datetime.now(UTC).timestamp()) + 60}, SECRET, algorithm="HS256")

    with pytest.raises(UnauthorizedError):
        decode_access_token(token, settings)


def test_rate_limiter_bloquea_al_superar_el_limite():
    limiter = LoginRateLimiter()

    limiter.check("correo|ip", 2)
    limiter.register_failure("correo|ip")
    limiter.register_failure("correo|ip")

    with pytest.raises(RateLimitedError) as error:
        limiter.check("correo|ip", 2)

    assert error.value.retry_after >= 1


def test_rate_limiter_reset_permite_nuevos_intentos():
    limiter = LoginRateLimiter()
    limiter.register_failure("correo|ip")
    limiter.register_failure("correo|ip")

    limiter.reset("correo|ip")
    limiter.check("correo|ip", 2)


def test_rate_limiter_clear_vacia_todo_el_estado():
    limiter = LoginRateLimiter()
    limiter.register_failure("correo|ip")

    limiter.clear()
    limiter.check("correo|ip", 1)
