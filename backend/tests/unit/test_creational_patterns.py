"""Patrones creacionales: Builder, Factory Method, Prototype y Singleton.

Abstract Factory (ESC-01) se cubre en tests/catalog/test_providers.py.
"""

from __future__ import annotations

import pytest

from app.auth.factory import GuestCreator, RegisteredCreator, creator_for
from app.core.config import AppRuntime, Settings, get_runtime, get_settings
from app.core.singleton import SingletonMeta
from app.listening.prototype import ListeningRecord
from app.playlists.builder import PlaylistBuilder


class TestPlaylistBuilder:
    def _builder(self) -> PlaylistBuilder:
        return PlaylistBuilder("u1", max_name_length=80, max_tracks=500)

    def test_build_valid_playlist(self):
        pl = (
            self._builder()
            .with_name("Salsa clásica")
            .add_track("sim_salsa_01")
            .add_track("sim_salsa_02")
            .build()
        )
        assert pl.name == "Salsa clásica"
        assert pl.track_ids == ("sim_salsa_01", "sim_salsa_02")

    def test_empty_name_rejected(self):
        with pytest.raises(ValueError):
            self._builder().with_name("   ")

    def test_name_over_limit_rejected(self):
        with pytest.raises(ValueError):
            PlaylistBuilder("u1", max_name_length=5, max_tracks=10).with_name("Demasiado largo")

    def test_too_many_tracks_rejected(self):
        builder = PlaylistBuilder("u1", max_name_length=80, max_tracks=1).with_name("Mix")
        builder.add_track("A")
        with pytest.raises(ValueError):
            builder.add_track("B")

    def test_build_without_name_rejected(self):
        with pytest.raises(ValueError):
            self._builder().add_track("x").build()

    def test_reorder_keeps_rn003(self):
        pl = self._builder().with_name("Mix").add_track("A").add_track("B").add_track("C").build()
        assert pl.reordered(2, 0).track_ids == ("C", "A", "B")


class TestUserFactory:
    def test_registered_ok(self):
        user = RegisteredCreator("EST@utp.edu.co", "clave1234", min_password_length=8).create_user()
        assert user.kind == "registered"
        assert user.email == "est@utp.edu.co"
        assert user.password_hashed is True

    def test_short_password_rejected(self):
        with pytest.raises(ValueError):
            RegisteredCreator("a@b.co", "corta", min_password_length=8).create_user()

    def test_duplicate_email_rejected(self):
        with pytest.raises(ValueError):
            RegisteredCreator(
                "est@utp.edu.co",
                "clave1234",
                {"EST@UTP.EDU.CO"},
                min_password_length=8,
            ).create_user()

    def test_guest_and_selector(self):
        assert GuestCreator().create_user().kind == "guest"
        assert creator_for("guest").create_user().kind == "guest"
        assert (
            creator_for("registered", email="x@y.co", password="clave1234", min_password_length=8)
            .create_user()
            .kind
            == "registered"
        )
        with pytest.raises(ValueError):
            creator_for("superuser")


class TestListeningPrototype:
    def test_skipped_rule_rn005(self):
        assert ListeningRecord("u1", "v1", 12).is_skipped(30) is True
        assert ListeningRecord("u1", "v1", 187).is_skipped(30) is False

    def test_clone_is_independent(self):
        proto = ListeningRecord("u1", "sim_rock_01", 180, genre="rock", artist="Art")
        clone = proto.clone(user_id="u2", track_id="sim_rock_02")
        assert (clone.user_id, clone.track_id, clone.seconds_listened) == (
            "u2",
            "sim_rock_02",
            180,
        )
        assert clone.genre == "rock"
        clone.seconds_listened = 5
        assert proto.seconds_listened == 180  # no aliasing
        assert clone.is_skipped(30) is True

    def test_negative_seconds_rejected(self):
        with pytest.raises(ValueError):
            ListeningRecord("u1", "v1", -1)


class TestSingleton:
    def test_get_settings_is_singleton(self):
        assert get_settings() is get_settings()

    def test_runtime_is_singleton(self):
        SingletonMeta.clear(AppRuntime)
        assert get_runtime() is get_runtime() is AppRuntime()

    def test_settings_instances_are_independent_models(self):
        # Settings como modelo sigue siendo instanciable (lo usan los tests de providers).
        assert Settings(music_provider="simulated").music_provider == "simulated"
