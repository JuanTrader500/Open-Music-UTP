"""Pruebas del núcleo transversal: salud, middlewares y arranque."""

from __future__ import annotations

import logging
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.core.database import get_db
from app.core.exceptions import ConfigurationError
from app.main import create_app


class _FakeSession:
    """Sesión falsa cuyo `execute` no hace nada (base disponible)."""

    def execute(self, *args: Any, **kwargs: Any) -> None:
        return None


class _BrokenSession:
    """Sesión falsa cuyo `execute` falla (base no disponible)."""

    def execute(self, *args: Any, **kwargs: Any) -> None:
        raise RuntimeError("base de datos no disponible")


def test_health_ok():
    response = TestClient(create_app()).get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_health_ready_con_base():
    app = create_app()
    app.dependency_overrides[get_db] = lambda: _FakeSession()
    try:
        response = TestClient(app).get("/api/health/ready")
    finally:
        app.dependency_overrides.clear()
    assert response.status_code == 200
    assert response.json() == {"status": "ready"}


def test_health_ready_sin_base():
    app = create_app()
    app.dependency_overrides[get_db] = lambda: _BrokenSession()
    try:
        response = TestClient(app).get("/api/health/ready")
    finally:
        app.dependency_overrides.clear()
    assert response.status_code == 503
    assert response.json()["code"] == "DB_UNAVAILABLE"


def test_request_id_se_genera_si_falta():
    response = TestClient(create_app()).get("/api/health")
    assert len(response.headers["X-Request-ID"]) == 32


def test_request_id_respeta_uno_valido():
    response = TestClient(create_app()).get("/api/health", headers={"X-Request-ID": "abc12345"})
    assert response.headers["X-Request-ID"] == "abc12345"


def test_request_id_ignora_uno_invalido():
    response = TestClient(create_app()).get("/api/health", headers={"X-Request-ID": "corto"})
    assert response.headers["X-Request-ID"] != "corto"
    assert len(response.headers["X-Request-ID"]) == 32


def test_cors_permite_origen_autorizado():
    response = TestClient(create_app()).get(
        "/api/health", headers={"Origin": "http://localhost:8080"}
    )
    assert response.headers.get("access-control-allow-origin") == "http://localhost:8080"


def test_cors_rechaza_origen_no_listado():
    response = TestClient(create_app()).get(
        "/api/health", headers={"Origin": "http://evil.example.com"}
    )
    assert "access-control-allow-origin" not in response.headers


def test_cabeceras_de_seguridad():
    response = TestClient(create_app()).get("/api/health")
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["X-Frame-Options"] == "DENY"
    assert response.headers["Referrer-Policy"] == "no-referrer"
    assert response.headers["Cache-Control"] == "no-store"


def test_cache_control_ausente_en_openapi():
    response = TestClient(create_app()).get("/api/openapi.json")
    assert "Cache-Control" not in response.headers


def test_arranque_falla_sin_jwt_secret(monkeypatch):
    monkeypatch.setenv("JWT_SECRET", "corto")
    get_settings.cache_clear()
    try:
        app = create_app()
        with pytest.raises(ConfigurationError), TestClient(app):
            pass
    finally:
        get_settings.cache_clear()


def test_log_no_incluye_authorization(caplog):
    client = TestClient(create_app())
    with caplog.at_level(logging.INFO):
        client.get("/api/health", headers={"Authorization": "Bearer secreto-123"})
    assert "secreto-123" not in caplog.text
    assert "Bearer" not in caplog.text
