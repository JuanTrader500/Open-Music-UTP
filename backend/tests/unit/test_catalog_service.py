"""Pruebas unitarias del servicio de catálogo (RF-010, RF-011, RN-012)."""

from __future__ import annotations

import pytest
from sqlalchemy import func, select

from app.catalog.models import Artist, GenreSeed, Track
from app.catalog.providers.models import TrackMetadata
from app.catalog.providers.music_provider import MusicProvider
from app.catalog.providers.simulated.factory import SimulatedProviderFactory
from app.catalog.service import CatalogService
from app.core.config import get_settings
from app.core.exceptions import InvalidQueryError, ValidationFailedError


class _ExplodingProvider:
    """Proveedor que falla si el servicio lo llama antes de validar."""

    def search_tracks(self, query: str, max_results: int | None = None):
        raise AssertionError("El proveedor no debe llamarse")

    def import_playlist(self, playlist_id: str, max_items: int = 50):
        raise AssertionError("El proveedor no debe llamarse")


def _service(db_session, provider=None) -> CatalogService:
    """Construye el servicio con el proveedor simulado."""
    settings = get_settings()
    return CatalogService(
        db_session,
        settings,
        provider=provider or MusicProvider(SimulatedProviderFactory(settings)),
    )


def test_busqueda_persiste_canciones_y_reutiliza_artista(db_session, catalog_genres):
    service = _service(db_session)

    result = service.search("cafeteros", 10)
    service.search("cafeteros", 10)

    assert result.total == 2
    assert {item.track_id for item in result.items} == {"sim_rock_01", "sim_rock_02"}
    assert all(item.artist.name == "Los Cafeteros Eléctricos" for item in result.items)
    assert all(item.genre.code == "sin_clasificar" for item in result.items)
    artists = db_session.scalar(
        select(func.count())
        .select_from(Artist)
        .where(Artist.name_normalized == "los cafeteros eléctricos")
    )
    assert artists == 1


def test_busqueda_descarta_canciones_no_embebibles(db_session, catalog_genres):
    service = _service(db_session)

    result = service.search("video", 10)

    assert result.total == 0
    assert result.items == []


def test_busqueda_corta_no_llama_al_proveedor(db_session, catalog_genres):
    service = _service(db_session, provider=_ExplodingProvider())

    with pytest.raises(InvalidQueryError):
        service.search("a", 10)


def test_limite_superior_al_configurado_es_invalido(db_session, catalog_genres):
    settings = get_settings()
    service = _service(db_session, provider=_ExplodingProvider())

    with pytest.raises(ValidationFailedError):
        service.search("rock", settings.youtube_max_results + 1)


def test_importacion_de_semilla_asigna_genero_y_es_idempotente(db_session, catalog_genres):
    service = _service(db_session)

    first = service.import_seed("PL_SIM_ROCK", "rock")
    second = service.import_seed("PL_SIM_ROCK", "rock")

    assert first == 3
    assert second == 3
    tracks = list(db_session.scalars(select(Track).where(Track.track_id.like("sim_rock_%"))))
    assert len(tracks) == 3
    assert all(track.genre_source == "seed" for track in tracks)
    assert all(track.genre_id == catalog_genres["rock"].id for track in tracks)
    seed = db_session.get(GenreSeed, "PL_SIM_ROCK")
    assert seed is not None
    assert seed.genre_id == catalog_genres["rock"].id

    result = service.search("cafeteros", 10)
    assert result.total == 2
    assert all(item.genre.code == "rock" for item in result.items)


def test_marcar_no_reproducible_lo_saca_de_la_busqueda(db_session, catalog_genres):
    service = _service(db_session)
    service.import_seed("PL_SIM_ROCK", "rock")
    assert service.search("rock", 10).total == 1

    service.mark_unplayable("sim_rock_03")

    assert service.search("rock", 10).total == 0
    detail = service.get_track("sim_rock_03")
    assert detail.is_embeddable is False


def test_la_importacion_de_semilla_restaura_un_reproducible(db_session, catalog_genres):
    service = _service(db_session)
    service.import_seed("PL_SIM_ROCK", "rock")
    service.mark_unplayable("sim_rock_03")

    service.import_seed("PL_SIM_ROCK", "rock")

    assert service.search("rock", 10).total == 1


def test_genero_se_infiere_de_otra_cancion_del_artista(db_session, catalog_genres):
    service = _service(db_session)
    service.import_seed("PL_SIM_ROCK", "rock")

    track = service._persist_track(
        TrackMetadata(
            track_id="sim_rock_nueva",
            title="Canción nueva",
            channel_title="Los Cafeteros Eléctricos",
            duration_s=180,
        )
    )

    assert track.genre_source == "artist"
    assert track.genre_id == catalog_genres["rock"].id


def test_listado_de_generos(db_session, catalog_genres):
    service = _service(db_session)

    genres = service.list_genres()

    assert {genre.code for genre in genres} == {"rock", "pop", "salsa", "sin_clasificar"}


def test_listado_de_artistas_filtra_por_genero(db_session, catalog_genres):
    service = _service(db_session)
    service.import_seed("PL_SIM_ROCK", "rock")
    service.import_seed("PL_SIM_POP", "pop")

    result = service.list_artists(
        genre_ids=str(catalog_genres["rock"].id),
        query=None,
        limit=50,
        offset=0,
    )

    assert result.total == 2
    assert {artist.name for artist in result.items} == {
        "Los Cafeteros Eléctricos",
        "Tormenta Cafetera",
    }
