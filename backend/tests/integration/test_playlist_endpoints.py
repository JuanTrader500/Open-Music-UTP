"""Pruebas de integración de los 8 endpoints de playlists (RF-013 a RF-015).

Requieren PostgreSQL de pruebas (`TEST_DATABASE_URL`). Usan las semillas
simuladas para que las pistas existan en el catálogo antes de agregarlas.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.catalog.providers.music_provider import MusicProvider
from app.catalog.providers.simulated.factory import SimulatedProviderFactory
from app.catalog.seed_importer import SEED_PLAYLISTS
from app.catalog.service import CatalogService
from app.core.config import get_settings

EMAIL_A = "playlists-a@example.com"
EMAIL_B = "playlists-b@example.com"
PASSWORD = "Clave-segura-123"
FIRST_TRACK = "sim_rock_01"
SECOND_TRACK = "sim_rock_02"


@pytest.fixture
def seeded_catalog(db_session, catalog_genres):
    """Carga las semillas simuladas en la misma sesión que usa el cliente HTTP."""
    settings = get_settings()
    service = CatalogService(
        db_session,
        settings,
        provider=MusicProvider(SimulatedProviderFactory(settings)),
    )
    for playlist_id, genre_code in SEED_PLAYLISTS.items():
        service.import_seed(playlist_id, genre_code)
    return catalog_genres


def _token(client: TestClient, email: str = EMAIL_A) -> str:
    """Registra una cuenta e inicia sesión para obtener el Bearer."""
    registered = client.post(
        "/api/auth/register",
        json={"email": email, "password": PASSWORD, "accept_privacy": True},
    )
    assert registered.status_code == 201
    response = client.post(
        "/api/auth/login",
        json={"email": email, "password": PASSWORD},
    )
    assert response.status_code == 200
    return response.json()["access_token"]


def _auth(token: str) -> dict[str, str]:
    """Cabecera Authorization con el token indicado."""
    return {"Authorization": f"Bearer {token}"}


def _create(client: TestClient, token: str, name: str = "Mi lista"):
    """Crea una playlist y devuelve la respuesta HTTP."""
    return client.post("/api/playlists", json={"name": name}, headers=_auth(token))


def _add(
    client: TestClient,
    token: str,
    playlist_id: str,
    track_id: str,
    *,
    confirm_duplicate: bool = False,
):
    """Agrega una canción a la playlist y devuelve la respuesta HTTP."""
    return client.post(
        f"/api/playlists/{playlist_id}/tracks",
        json={"track_id": track_id, "confirm_duplicate": confirm_duplicate},
        headers=_auth(token),
    )


def _detail(client: TestClient, token: str, playlist_id: str):
    """Pide el detalle de una playlist."""
    return client.get(f"/api/playlists/{playlist_id}", headers=_auth(token))


def test_flujo_completo_crud_pistas_y_orden(client: TestClient, seeded_catalog):
    token = _token(client)

    created = _create(client, token, "  Salsa UTP  ")
    assert created.status_code == 201
    playlist = created.json()
    playlist_id = playlist["id"]
    assert playlist["name"] == "Salsa UTP"
    assert playlist["tracks"] == [] and playlist["total"] == 0

    listed = client.get("/api/playlists", headers=_auth(token))
    assert listed.status_code == 200
    assert listed.json()["total"] == 1
    assert listed.json()["items"][0]["track_count"] == 0

    first_added = _add(client, token, playlist_id, FIRST_TRACK)
    assert first_added.status_code == 201
    first = first_added.json()["tracks"][0]
    assert first["position"] == 1
    assert first["track_id"] == FIRST_TRACK
    assert first["artist"]["name"] and first["genre"]["code"] == "rock"

    second_added = _add(client, token, playlist_id, SECOND_TRACK)
    assert second_added.status_code == 201
    assert second_added.json()["total"] == 2

    detail = _detail(client, token, playlist_id)
    assert detail.status_code == 200
    ids = [track["playlist_track_id"] for track in detail.json()["tracks"]]
    assert [track["position"] for track in detail.json()["tracks"]] == [1, 2]

    renamed = client.patch(
        f"/api/playlists/{playlist_id}",
        json={"name": "Rock UTP"},
        headers=_auth(token),
    )
    assert renamed.status_code == 200
    assert renamed.json()["name"] == "Rock UTP"

    reordered = client.put(
        f"/api/playlists/{playlist_id}/tracks/order",
        json={"playlist_track_ids": list(reversed(ids))},
        headers=_auth(token),
    )
    assert reordered.status_code == 200
    assert [track["track_id"] for track in reordered.json()["tracks"]] == [
        SECOND_TRACK,
        FIRST_TRACK,
    ]
    assert [track["position"] for track in reordered.json()["tracks"]] == [1, 2]

    first_in_new_order = reordered.json()["tracks"][0]["playlist_track_id"]
    removed = client.delete(
        f"/api/playlists/{playlist_id}/tracks/{first_in_new_order}",
        headers=_auth(token),
    )
    assert removed.status_code == 204

    after_remove = _detail(client, token, playlist_id).json()
    assert after_remove["total"] == 1
    assert after_remove["tracks"][0]["track_id"] == FIRST_TRACK
    assert after_remove["tracks"][0]["position"] == 1

    no_confirm = client.delete(f"/api/playlists/{playlist_id}", headers=_auth(token))
    assert no_confirm.status_code == 409
    assert no_confirm.json()["code"] == "CONFIRMATION_REQUIRED"

    deleted = client.delete(
        f"/api/playlists/{playlist_id}?confirm=true",
        headers=_auth(token),
    )
    assert deleted.status_code == 204
    assert client.get("/api/playlists", headers=_auth(token)).json()["total"] == 0

    # RF-015: borrar la playlist no borra las canciones del catálogo.
    assert client.get(f"/api/catalog/tracks/{FIRST_TRACK}").status_code == 200


def test_crear_rechaza_nombre_en_blanco(client: TestClient):
    token = _token(client)

    response = _create(client, token, "   ")

    assert response.status_code == 422
    assert response.json()["code"] == "VALIDATION_ERROR"


def test_playlists_requieren_autenticacion(client: TestClient):
    response = client.get("/api/playlists")

    assert response.status_code == 401
    assert response.json()["code"] == "UNAUTHORIZED"


def test_uuid_invalido_devuelve_422(client: TestClient):
    token = _token(client)

    response = client.get("/api/playlists/no-es-uuid", headers=_auth(token))

    assert response.status_code == 422
    assert response.json()["code"] == "VALIDATION_ERROR"


def test_agregar_cancion_inexistente_devuelve_404(client: TestClient, seeded_catalog):
    token = _token(client)
    playlist_id = _create(client, token).json()["id"]

    response = _add(client, token, playlist_id, "no_existe")

    assert response.status_code == 404
    assert response.json()["code"] == "TRACK_NOT_FOUND"


def test_duplicado_pide_confirmacion_y_luego_se_agrega(client: TestClient, seeded_catalog):
    token = _token(client)
    playlist_id = _create(client, token).json()["id"]
    assert _add(client, token, playlist_id, FIRST_TRACK).status_code == 201

    duplicate = _add(client, token, playlist_id, FIRST_TRACK)
    assert duplicate.status_code == 409
    assert duplicate.json()["code"] == "DUPLICATE_TRACK"

    confirmed = _add(client, token, playlist_id, FIRST_TRACK, confirm_duplicate=True)
    assert confirmed.status_code == 201
    assert confirmed.json()["total"] == 2
    assert [track["position"] for track in confirmed.json()["tracks"]] == [1, 2]


def test_reordenar_rechaza_faltantes_repetidos_o_ajenos(client: TestClient, seeded_catalog):
    token = _token(client)
    playlist_id = _create(client, token).json()["id"]
    _add(client, token, playlist_id, FIRST_TRACK)
    _add(client, token, playlist_id, SECOND_TRACK)
    ids = [
        track["playlist_track_id"] for track in _detail(client, token, playlist_id).json()["tracks"]
    ]

    invalid_orders = [
        ids[:-1],
        [ids[0], ids[0]],
        [ids[0], 999_999],
    ]
    for invalid in invalid_orders:
        response = client.put(
            f"/api/playlists/{playlist_id}/tracks/order",
            json={"playlist_track_ids": invalid},
            headers=_auth(token),
        )
        assert response.status_code == 422
        assert response.json()["code"] == "VALIDATION_ERROR"


def test_playlist_ajena_no_es_visible_ni_modificable(client: TestClient, seeded_catalog):
    owner_token = _token(client, EMAIL_A)
    other_token = _token(client, EMAIL_B)
    playlist_id = _create(client, owner_token).json()["id"]

    assert _detail(client, other_token, playlist_id).status_code == 404
    assert (
        client.patch(
            f"/api/playlists/{playlist_id}",
            json={"name": "Intruso"},
            headers=_auth(other_token),
        ).status_code
        == 404
    )
    assert (
        client.delete(
            f"/api/playlists/{playlist_id}?confirm=true",
            headers=_auth(other_token),
        ).status_code
        == 404
    )
    assert _add(client, other_token, playlist_id, FIRST_TRACK).status_code == 404
    assert (
        client.put(
            f"/api/playlists/{playlist_id}/tracks/order",
            json={"playlist_track_ids": []},
            headers=_auth(other_token),
        ).status_code
        == 404
    )

    assert client.get("/api/playlists", headers=_auth(other_token)).json()["total"] == 0


def test_quitar_pista_de_otra_playlist_devuelve_404(client: TestClient, seeded_catalog):
    token = _token(client)
    first_id = _create(client, token, "Primera").json()["id"]
    second_id = _create(client, token, "Segunda").json()["id"]
    foreign_track_id = _add(client, token, second_id, FIRST_TRACK).json()["tracks"][0][
        "playlist_track_id"
    ]

    response = client.delete(
        f"/api/playlists/{first_id}/tracks/{foreign_track_id}",
        headers=_auth(token),
    )

    assert response.status_code == 404
    assert response.json()["code"] == "NOT_FOUND"
