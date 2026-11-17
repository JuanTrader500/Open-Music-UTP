"""Pruebas de integración de los 6 endpoints de auth (RF-017/018/022)."""

from __future__ import annotations

from fastapi.testclient import TestClient

EMAIL = "ana@example.com"
PASSWORD = "Clave-segura-123"


def _register(client: TestClient, email: str = EMAIL, password: str = PASSWORD):
    """Registra una cuenta de prueba y devuelve la respuesta."""
    return client.post(
        "/api/auth/register",
        json={"email": email, "password": password, "accept_privacy": True},
    )


def _login(client: TestClient, email: str = EMAIL, password: str = PASSWORD):
    """Inicia sesión y devuelve la respuesta."""
    return client.post(
        "/api/auth/login",
        json={"email": email, "password": password},
    )


def _token(client: TestClient, email: str = EMAIL, password: str = PASSWORD) -> str:
    """Registra (si hace falta) e inicia sesión para obtener un token."""
    _register(client, email=email, password=password)
    response = _login(client, email=email, password=password)
    assert response.status_code == 200
    return response.json()["access_token"]


def _auth(token: str) -> dict[str, str]:
    """Cabecera Authorization con el token indicado."""
    return {"Authorization": f"Bearer {token}"}


def test_registro_exitoso(client: TestClient):
    response = _register(client, email="Ana@Example.com")

    assert response.status_code == 201
    body = response.json()
    assert body["email"] == "ana@example.com"
    assert body["id"]
    assert body["created_at"]
    assert "password" not in body


def test_registro_rechaza_privacidad_no_aceptada(client: TestClient):
    response = client.post(
        "/api/auth/register",
        json={"email": EMAIL, "password": PASSWORD, "accept_privacy": False},
    )

    assert response.status_code == 422
    assert response.json()["code"] == "VALIDATION_ERROR"


def test_registro_rechaza_password_corta(client: TestClient):
    response = _register(client, password="corta")

    assert response.status_code == 422
    assert response.json()["code"] == "VALIDATION_ERROR"


def test_registro_rechaza_correo_invalido(client: TestClient):
    response = _register(client, email="sin-arroba")

    assert response.status_code == 422
    assert response.json()["code"] == "VALIDATION_ERROR"


def test_registro_rechaza_correo_duplicado_normalizado(client: TestClient):
    assert _register(client, email="Ana@Example.com").status_code == 201

    response = _register(client, email="ana@example.com")

    assert response.status_code == 409
    assert response.json()["code"] == "EMAIL_TAKEN"


def test_login_exitoso(client: TestClient):
    _register(client)

    response = _login(client, email="ANA@EXAMPLE.COM")

    assert response.status_code == 200
    body = response.json()
    assert body["access_token"]
    assert body["token_type"] == "bearer"
    assert body["expires_in"] == 3600


def test_login_rechaza_credenciales_incorrectas(client: TestClient):
    _register(client)

    response = _login(client, password="Otra-clave-123")

    assert response.status_code == 401
    assert response.json()["code"] == "INVALID_CREDENTIALS"


def test_me_requiere_token(client: TestClient):
    response = client.get("/api/auth/me")

    assert response.status_code == 401
    assert response.json()["code"] == "UNAUTHORIZED"


def test_me_rechaza_token_invalido(client: TestClient):
    response = client.get("/api/auth/me", headers=_auth("token-invalido"))

    assert response.status_code == 401
    assert response.json()["code"] == "UNAUTHORIZED"


def test_me_devuelve_el_usuario_autenticado(client: TestClient):
    token = _token(client)

    response = client.get("/api/auth/me", headers=_auth(token))

    assert response.status_code == 200
    body = response.json()
    assert body["email"] == EMAIL
    assert body["is_simulated"] is False


def test_logout(client: TestClient):
    token = _token(client)

    response = client.post("/api/auth/logout", headers=_auth(token))

    assert response.status_code == 204
    assert response.content == b""


def test_export_incluye_usuario_y_colecciones_vacias(client: TestClient):
    token = _token(client)

    response = client.get("/api/auth/export", headers=_auth(token))

    assert response.status_code == 200
    body = response.json()
    assert body["user"]["email"] == EMAIL
    assert body["playlists"] == []
    assert body["favorites"] == []
    assert body["listening_events"] == []
    assert body["preferences"] == {"genres": [], "artists": []}


def test_delete_account_elimina_la_cuenta(client: TestClient):
    token = _token(client)

    response = client.delete("/api/auth/account", headers=_auth(token))

    assert response.status_code == 204
    assert response.content == b""

    assert _login(client).status_code == 401
    assert client.get("/api/auth/me", headers=_auth(token)).status_code == 401


def test_login_bloquea_tras_cinco_intentos_fallidos(client: TestClient):
    for _ in range(5):
        response = _login(client, email="desconocido@example.com")
        assert response.status_code == 401

    blocked = _login(client, email="desconocido@example.com")

    assert blocked.status_code == 429
    assert blocked.json()["code"] == "RATE_LIMITED"
    assert "Retry-After" in blocked.headers
