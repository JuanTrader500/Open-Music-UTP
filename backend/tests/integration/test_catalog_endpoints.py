"""Pruebas de integración de las 5 rutas de catálogo (RF-010, RF-011, RF-012)."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.catalog.providers.music_provider import MusicProvider
from app.catalog.providers.simulated.factory import SimulatedProviderFactory
from app.catalog.seed_importer import SEED_PLAYLISTS
from app.catalog.service import CatalogService
from app.core.config import get_settings


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


def test_busqueda_devuelve_y_persiste_canciones(client: TestClient, seeded_catalog):
    response = client.get("/api/catalog/search", params={"q": "cafeteros", "limit": 10})

    assert response.status_code == 200
    body = response.json()
    assert body["query"] == "cafeteros"
    assert body["total"] == 2
    assert len(body["items"]) == 2
    first = body["items"][0]
    assert first["track_id"] == "sim_rock_01"
    assert first["artist"]["name"] == "Los Cafeteros Eléctricos"
    assert first["genre"]["code"] == "rock"
    assert first["is_embeddable"] is True

    detail = client.get(f"/api/catalog/tracks/{first['track_id']}")
    assert detail.status_code == 200
    assert detail.json()["title"] == first["title"]


def test_busqueda_corta_devuelve_invalid_query(client: TestClient):
    response = client.get("/api/catalog/search", params={"q": "a"})

    assert response.status_code == 422
    assert response.json()["code"] == "INVALID_QUERY"


def test_busqueda_con_limite_excesivo_devuelve_validation_error(client: TestClient):
    settings = get_settings()

    response = client.get(
        "/api/catalog/search",
        params={"q": "rock", "limit": settings.youtube_max_results + 1},
    )

    assert response.status_code == 422
    assert response.json()["code"] == "VALIDATION_ERROR"


def test_detalle_de_track_inexistente(client: TestClient):
    response = client.get("/api/catalog/tracks/no-existe")

    assert response.status_code == 404
    assert response.json()["code"] == "TRACK_NOT_FOUND"


def test_marcar_no_reproducible_lo_saca_de_la_busqueda(client: TestClient, seeded_catalog):
    marked = client.post("/api/catalog/tracks/sim_rock_03/unplayable")
    assert marked.status_code == 204
    assert marked.content == b""

    search = client.get("/api/catalog/search", params={"q": "rock"})
    assert search.status_code == 200
    assert search.json()["total"] == 0

    detail = client.get("/api/catalog/tracks/sim_rock_03")
    assert detail.status_code == 200
    assert detail.json()["is_embeddable"] is False


def test_listado_de_generos(client: TestClient, catalog_genres):
    response = client.get("/api/catalog/genres")

    assert response.status_code == 200
    body = response.json()
    assert {genre["code"] for genre in body} == {
        "rock",
        "pop",
        "salsa",
        "sin_clasificar",
    }


def test_listado_de_artistas_y_filtros(client: TestClient, seeded_catalog):
    all_artists = client.get("/api/catalog/artists", params={"limit": 50})
    assert all_artists.status_code == 200
    assert all_artists.json()["total"] == 4

    rock = seeded_catalog["rock"]
    by_genre = client.get(
        "/api/catalog/artists",
        params={"genre_ids": str(rock.id), "limit": 50},
    )
    assert by_genre.status_code == 200
    assert by_genre.json()["total"] == 2
    assert {artist["name"] for artist in by_genre.json()["items"]} == {
        "Los Cafeteros Eléctricos",
        "Tormenta Cafetera",
    }

    by_name = client.get("/api/catalog/artists", params={"q": "valentina"})
    assert by_name.status_code == 200
    assert by_name.json()["total"] == 1
    assert by_name.json()["items"][0]["name"] == "Valentina Mora"


def test_artistas_con_genero_invalido(client: TestClient):
    response = client.get("/api/catalog/artists", params={"genre_ids": "1,abc"})

    assert response.status_code == 422
    assert response.json()["code"] == "VALIDATION_ERROR"


def test_catalogo_no_requiere_token(client: TestClient):
    response = client.get("/api/catalog/genres")

    assert response.status_code == 200
