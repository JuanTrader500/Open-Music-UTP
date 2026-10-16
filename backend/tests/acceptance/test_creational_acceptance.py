"""Aceptación de creación de objetos: un escenario Given/When/Then por RF (sin red).

Trazabilidad: docs/requerimientos-funcionales.md (ESC-01 a ESC-05).
ESC-01 usa el proveedor simulado (RNF-033: sin cuota).
"""
from __future__ import annotations

from app.auth.factory import GuestCreator, RegisteredCreator
from app.catalog.providers.music_provider import MusicProvider
from app.catalog.providers.simulated.factory import SimulatedProviderFactory
from app.core.config import Settings, get_runtime
from app.core.exceptions import InvalidQueryError
from app.listening.prototype import ListeningRecord
from app.playlists.builder import PlaylistBuilder


def test_esc01_busqueda_exitosa():
    # Given un invitado con proveedor simulado
    provider = MusicProvider(SimulatedProviderFactory())
    # When busca "cafeteros"
    tracks = provider.search_tracks("cafeteros")
    # Then recibe orden + metadatos
    assert [t.video_id for t in tracks] == ["sim_rock_01", "sim_rock_02"]
    assert all(t.title and t.duration_s >= 0 for t in tracks)


def test_esc01_consulta_invalida_no_gasta_cuota():
    provider = MusicProvider(SimulatedProviderFactory())
    try:
        provider.search_tracks("a")
    except InvalidQueryError:
        pass
    else:
        raise AssertionError("Debió lanzar InvalidQueryError (RF-010)")


def test_esc01_playlist_filtra_no_embebible():
    provider = MusicProvider(SimulatedProviderFactory())
    tracks = provider.import_playlist("PL_SIM_SALSA")
    assert [t.video_id for t in tracks] == ["sim_salsa_01", "sim_salsa_02"]


def test_esc02_crear_playlist():
    # Given usuario registrado / When crea playlist / Then queda con 2 pistas
    pl = (
        PlaylistBuilder("u1")
        .with_name("Salsa clásica")
        .with_description("Para el fin de semana")
        .add_track("sim_salsa_01")
        .add_track("sim_salsa_02")
        .build()
    )
    assert pl.track_ids == ("sim_salsa_01", "sim_salsa_02")


def test_esc03_registro_e_invitado():
    # Given visitante / When se registra / Then queda registrado con hash
    user = RegisteredCreator("est@utp.edu.co", "clave1234").create_user()
    assert user.kind == "registered" and user.password_hashed
    # When continúa como invitado / Then permisos limitados
    guest = GuestCreator().create_user()
    assert guest.kind == "guest" and guest.can_persist is False


def test_esc04_escucha_y_clon():
    # Given 187 s de rock / When se registra / Then no omitida
    rec = ListeningRecord("u1", "sim_rock_01", 187, genre="rock")
    assert rec.skipped is False
    # Given 12 s / Then omitida (RN-005)
    assert ListeningRecord("u1", "sim_rock_02", 12).skipped is True
    # When se clona para simulación / Then independiente
    clone = rec.clone(user_id="u2", video_id="sim_rock_02")
    assert clone.user_id == "u2" and clone.seconds_listened == 187


def test_esc05_config_unica():
    rt1 = get_runtime(Settings(music_provider="simulated"))
    rt2 = get_runtime()
    assert rt1 is rt2
    assert rt2.settings.music_provider == "simulated"
