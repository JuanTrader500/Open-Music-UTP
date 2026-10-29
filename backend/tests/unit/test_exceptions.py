"""Pruebas de las excepciones de dominio y de sus respuestas HTTP."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.exceptions import MusicAppError, NotFoundError, RateLimitedError
from app.main import create_app


def _client_with(case: str) -> TestClient:
    """Crea un cliente con una ruta temporal que provoca el caso indicado."""
    app = create_app()

    @app.get("/api/_test/endpoint")
    def _endpoint(n: int | None = None) -> dict[str, int | None]:
        if case == "domain":
            raise NotFoundError()
        if case == "rate":
            raise RateLimitedError(retry_after=17)
        if case == "unexpected":
            raise RuntimeError("detalle-interno-secreto")
        return {"n": n}

    return _client(app, case)


def _client(app: FastAPI, case: str) -> TestClient:
    """Devuelve el cliente adecuado; el caso no controlado no re-lanza errores."""
    return TestClient(app, raise_server_exceptions=case != "unexpected")


def test_error_de_dominio():
    response = _client_with("domain").get("/api/_test/endpoint")
    assert response.status_code == 404
    assert set(response.json().keys()) == {"code", "message"}
    assert response.json()["code"] == "NOT_FOUND"


def test_error_de_validacion():
    response = _client_with("validation").get("/api/_test/endpoint", params={"n": "texto"})
    assert response.status_code == 422
    assert set(response.json().keys()) == {"code", "message"}
    assert response.json()["code"] == "VALIDATION_ERROR"


def test_error_no_controlado():
    response = _client_with("unexpected").get("/api/_test/endpoint")
    assert response.status_code == 500
    assert response.json() == {
        "code": "INTERNAL_ERROR",
        "message": "Ocurrió un error inesperado. Intenta de nuevo.",
    }
    assert "detalle-interno-secreto" not in response.text


def test_rate_limited_envia_retry_after():
    response = _client_with("rate").get("/api/_test/endpoint")
    assert response.status_code == 429
    assert response.headers["Retry-After"] == "17"
    assert response.json()["code"] == "RATE_LIMITED"


def test_music_app_error_usa_mensaje_por_defecto():
    error = MusicAppError()
    assert error.code == "INTERNAL_ERROR"
    assert error.message == "Ocurrió un error inesperado. Intenta de nuevo."
    assert str(error) == error.message


def test_metodo_no_permitido():
    response = _client_with("validation").post("/api/_test/endpoint")
    assert response.status_code == 405
    assert response.json()["code"] == "METHOD_NOT_ALLOWED"


def test_ruta_inexistente():
    response = _client_with("validation").get("/api/_test/no-existe")
    assert response.status_code == 404
    assert response.json()["code"] == "NOT_FOUND"
