"""Pruebas unitarias de la fachada de playlists (entrega 2, RF-013 a RF-015).

Usan un repositorio y un catálogo falsos para probar la coordinación, los
límites y los permisos sin base de datos. Las pruebas de integración cubren los
endpoints y el reordenamiento real con PostgreSQL.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from types import SimpleNamespace

import pytest

from app.core.config import Settings
from app.core.exceptions import (
    ConfirmationRequiredError,
    DuplicateTrackError,
    NotFoundError,
    PlaylistLimitError,
    TrackLimitError,
    TrackNotFoundError,
    ValidationFailedError,
)
from app.playlists.schemas import PlaylistNameIn, PlaylistReorder, PlaylistTrackAdd
from app.playlists.service import PlaylistService


class _FakeDb:
    """Sesión falsa que cuenta commit y rollback del decorador."""

    def __init__(self) -> None:
        self.commits = 0
        self.rollbacks = 0

    def commit(self) -> None:
        self.commits += 1

    def rollback(self) -> None:
        self.rollbacks += 1


class _FakeCatalog:
    """Catálogo mínimo: solo valida que la canción exista (RF-014)."""

    def __init__(self, *track_ids: str) -> None:
        self.tracks = {track_id: SimpleNamespace(track_id=track_id) for track_id in track_ids}

    def get_track(self, track_id: str) -> SimpleNamespace:
        if track_id not in self.tracks:
            raise TrackNotFoundError()
        return self.tracks[track_id]


class _FakeRepository:
    """Repositorio en memoria con la misma superficie que `PlaylistRepository`."""

    def __init__(self) -> None:
        self.playlists: dict[uuid.UUID, SimpleNamespace] = {}
        self.playlist_tracks: dict[int, SimpleNamespace] = {}
        self._next_id = 1

    def count_for_user(self, user_id: uuid.UUID) -> int:
        return sum(1 for playlist in self.playlists.values() if playlist.user_id == user_id)

    def list_for_user(self, user_id: uuid.UUID) -> list[tuple[SimpleNamespace, int]]:
        return [
            (playlist, self._count_tracks(playlist.id))
            for playlist in self.playlists.values()
            if playlist.user_id == user_id
        ]

    def get_owned(self, playlist_id: uuid.UUID, user_id: uuid.UUID) -> SimpleNamespace | None:
        playlist = self.playlists.get(playlist_id)
        return playlist if playlist is not None and playlist.user_id == user_id else None

    def create(self, user_id: uuid.UUID, name: str) -> SimpleNamespace:
        playlist = SimpleNamespace(
            id=uuid.uuid4(),
            user_id=user_id,
            name=name,
            created_at=datetime.now(UTC),
        )
        self.playlists[playlist.id] = playlist
        return playlist

    def rename(self, playlist: SimpleNamespace, name: str) -> None:
        playlist.name = name

    def delete(self, playlist: SimpleNamespace) -> None:
        self.playlists.pop(playlist.id, None)
        for track_id in [
            key for key, track in self.playlist_tracks.items() if track.playlist_id == playlist.id
        ]:
            del self.playlist_tracks[track_id]

    def list_playlist_track_ids(self, playlist_id: uuid.UUID) -> list[int]:
        return [track.id for track in self._ordered_tracks(playlist_id)]

    def list_track_ids(self, playlist_id: uuid.UUID) -> list[str]:
        return [track.track_id for track in self._ordered_tracks(playlist_id)]

    def has_track(self, playlist_id: uuid.UUID, track_id: str) -> bool:
        return track_id in self.list_track_ids(playlist_id)

    def next_position(self, playlist_id: uuid.UUID) -> int:
        return len(self._ordered_tracks(playlist_id)) + 1

    def add_track(
        self,
        playlist_id: uuid.UUID,
        track_id: str,
        position: int,
    ) -> SimpleNamespace:
        playlist_track = SimpleNamespace(
            id=self._next_id,
            playlist_id=playlist_id,
            track_id=track_id,
            position=position,
        )
        self._next_id += 1
        self.playlist_tracks[playlist_track.id] = playlist_track
        return playlist_track

    def get_playlist_track(
        self,
        playlist_id: uuid.UUID,
        playlist_track_id: int,
    ) -> SimpleNamespace | None:
        playlist_track = self.playlist_tracks.get(playlist_track_id)
        if playlist_track is None or playlist_track.playlist_id != playlist_id:
            return None
        return playlist_track

    def remove_track(self, playlist_track: SimpleNamespace) -> None:
        removed_position = playlist_track.position
        del self.playlist_tracks[playlist_track.id]
        for track in self.playlist_tracks.values():
            if (
                track.playlist_id == playlist_track.playlist_id
                and track.position > removed_position
            ):
                track.position -= 1

    def apply_order(self, playlist_id: uuid.UUID, ordered_ids: list[int]) -> None:
        for position, playlist_track_id in enumerate(ordered_ids, start=1):
            self.playlist_tracks[playlist_track_id].position = position

    def list_tracks_with_metadata(
        self,
        playlist_id: uuid.UUID,
    ) -> list[tuple[SimpleNamespace, SimpleNamespace, SimpleNamespace, SimpleNamespace]]:
        rows = []
        for playlist_track in self._ordered_tracks(playlist_id):
            track = SimpleNamespace(
                track_id=playlist_track.track_id,
                title=f"Título {playlist_track.track_id}",
                duration_s=180,
                view_count=10,
                like_count=2,
                thumbnail_url="https://img",
                is_embeddable=True,
            )
            artist = SimpleNamespace(id=1, name="Artista")
            genre = SimpleNamespace(id=1, code="rock", name="Rock")
            rows.append((playlist_track, track, artist, genre))
        return rows

    def _ordered_tracks(self, playlist_id: uuid.UUID) -> list[SimpleNamespace]:
        return sorted(
            (track for track in self.playlist_tracks.values() if track.playlist_id == playlist_id),
            key=lambda track: track.position,
        )

    def _count_tracks(self, playlist_id: uuid.UUID) -> int:
        return sum(1 for track in self.playlist_tracks.values() if track.playlist_id == playlist_id)


def _settings(**overrides) -> Settings:
    base = {
        "playlist_name_max_length": 20,
        "max_playlists_per_user": 2,
        "max_tracks_per_playlist": 3,
    }
    base.update(overrides)
    return Settings(**base)


def _user() -> SimpleNamespace:
    return SimpleNamespace(id=uuid.uuid4())


def _service(
    *,
    settings: Settings | None = None,
    repository: _FakeRepository | None = None,
    catalog: _FakeCatalog | None = None,
) -> tuple[PlaylistService, _FakeDb, _FakeRepository]:
    db = _FakeDb()
    repo = repository or _FakeRepository()
    service = PlaylistService(
        db,
        settings or _settings(),
        repository=repo,
        catalog=catalog or _FakeCatalog("t1", "t2", "t3"),
    )
    return service, db, repo


# ------------------------------------- Creación -------------------------------------------
def test_create_playlist_returns_empty_detail_and_commits():
    service, db, repository = _service()
    user = _user()

    detail = service.create_playlist(user, PlaylistNameIn(name="  Salsa  "))

    assert detail.name == "Salsa"
    assert detail.tracks == [] and detail.total == 0
    assert repository.count_for_user(user.id) == 1
    assert (db.commits, db.rollbacks) == (1, 0)


@pytest.mark.parametrize("name", ["   ", "x" * 21])
def test_create_rejects_invalid_name(name):
    service, db, repository = _service()

    with pytest.raises(ValidationFailedError):
        service.create_playlist(_user(), PlaylistNameIn(name=name))

    assert repository.playlists == {}
    assert (db.commits, db.rollbacks) == (0, 1)


def test_create_rejects_when_playlist_limit_is_reached():
    user = _user()
    repository = _FakeRepository()
    repository.create(user.id, "A")
    repository.create(user.id, "B")
    service, db, _ = _service(repository=repository, settings=_settings(max_playlists_per_user=2))

    with pytest.raises(PlaylistLimitError):
        service.create_playlist(user, PlaylistNameIn(name="C"))

    assert repository.count_for_user(user.id) == 2
    assert db.rollbacks == 1


def test_list_only_returns_the_user_playlists():
    owner, other = _user(), _user()
    repository = _FakeRepository()
    repository.create(owner.id, "Mía")
    repository.create(other.id, "Ajena")
    service, _, _ = _service(repository=repository)

    result = service.list_playlists(owner)

    assert result.total == 1
    assert result.items[0].name == "Mía"


# --------------------------------------- Pistas -------------------------------------------
def test_add_track_appends_with_position_one():
    user = _user()
    repository = _FakeRepository()
    playlist = repository.create(user.id, "Mix")
    service, db, _ = _service(repository=repository)

    detail = service.add_track(user, playlist.id, PlaylistTrackAdd(track_id="t1"))

    assert detail.total == 1
    assert detail.tracks[0].track_id == "t1"
    assert detail.tracks[0].position == 1
    assert db.commits == 1


def test_add_missing_track_returns_not_found():
    user = _user()
    repository = _FakeRepository()
    playlist = repository.create(user.id, "Mix")
    service, db, _ = _service(repository=repository, catalog=_FakeCatalog("t1"))

    with pytest.raises(TrackNotFoundError):
        service.add_track(user, playlist.id, PlaylistTrackAdd(track_id="no-existe"))

    assert repository.playlist_tracks == {}
    assert db.rollbacks == 1


def test_duplicate_requires_confirmation():
    user = _user()
    repository = _FakeRepository()
    playlist = repository.create(user.id, "Mix")
    repository.add_track(playlist.id, "t1", 1)
    service, db, _ = _service(repository=repository)

    with pytest.raises(DuplicateTrackError):
        service.add_track(user, playlist.id, PlaylistTrackAdd(track_id="t1"))

    assert len(repository.playlist_tracks) == 1
    assert db.rollbacks == 1


def test_duplicate_with_confirmation_is_added():
    user = _user()
    repository = _FakeRepository()
    playlist = repository.create(user.id, "Mix")
    repository.add_track(playlist.id, "t1", 1)
    service, _, _ = _service(repository=repository)

    detail = service.add_track(
        user,
        playlist.id,
        PlaylistTrackAdd(track_id="t1", confirm_duplicate=True),
    )

    assert detail.total == 2
    assert [track.position for track in detail.tracks] == [1, 2]
    assert [track.track_id for track in detail.tracks] == ["t1", "t1"]


def test_add_track_rejects_when_track_limit_is_reached():
    user = _user()
    repository = _FakeRepository()
    playlist = repository.create(user.id, "Mix")
    repository.add_track(playlist.id, "t1", 1)
    service, db, _ = _service(
        repository=repository,
        settings=_settings(max_tracks_per_playlist=1),
    )

    with pytest.raises(TrackLimitError):
        service.add_track(user, playlist.id, PlaylistTrackAdd(track_id="t2"))

    assert len(repository.playlist_tracks) == 1
    assert db.rollbacks == 1


def test_remove_track_keeps_positions_consecutive():
    user = _user()
    repository = _FakeRepository()
    playlist = repository.create(user.id, "Mix")
    for position, track_id in enumerate(("t1", "t2", "t3"), start=1):
        repository.add_track(playlist.id, track_id, position)
    second = repository.list_playlist_track_ids(playlist.id)[1]
    service, db, _ = _service(repository=repository)

    service.remove_track(user, playlist.id, second)

    detail = service.get_playlist(user, playlist.id)
    assert [track.track_id for track in detail.tracks] == ["t1", "t3"]
    assert [track.position for track in detail.tracks] == [1, 2]
    assert db.commits == 1


def test_remove_track_from_another_playlist_returns_not_found():
    user = _user()
    repository = _FakeRepository()
    first = repository.create(user.id, "Primera")
    second = repository.create(user.id, "Segunda")
    foreign = repository.add_track(second.id, "t1", 1)
    service, db, _ = _service(repository=repository)

    with pytest.raises(NotFoundError):
        service.remove_track(user, first.id, foreign.id)

    assert db.rollbacks == 1


# ------------------------------------- Reordenar ------------------------------------------
def test_reorder_updates_positions_and_order():
    user = _user()
    repository = _FakeRepository()
    playlist = repository.create(user.id, "Mix")
    for position, track_id in enumerate(("t1", "t2", "t3"), start=1):
        repository.add_track(playlist.id, track_id, position)
    current_ids = repository.list_playlist_track_ids(playlist.id)
    service, db, _ = _service(repository=repository)

    detail = service.reorder_tracks(
        user,
        playlist.id,
        PlaylistReorder(playlist_track_ids=list(reversed(current_ids))),
    )

    assert [track.track_id for track in detail.tracks] == ["t3", "t2", "t1"]
    assert [track.position for track in detail.tracks] == [1, 2, 3]
    assert db.commits == 1


def test_reorder_rejects_missing_repeated_or_foreign_ids():
    user = _user()
    repository = _FakeRepository()
    playlist = repository.create(user.id, "Mix")
    for position, track_id in enumerate(("t1", "t2", "t3"), start=1):
        repository.add_track(playlist.id, track_id, position)
    current_ids = repository.list_playlist_track_ids(playlist.id)
    service, _, _ = _service(repository=repository)

    invalid_orders = [
        current_ids[:-1],
        [current_ids[0], current_ids[0], current_ids[1]],
        [current_ids[0], current_ids[1], 999],
    ]
    for invalid in invalid_orders:
        with pytest.raises(ValidationFailedError):
            service.reorder_tracks(
                user,
                playlist.id,
                PlaylistReorder(playlist_track_ids=invalid),
            )


# ---------------------------------- Propiedad y borrado -----------------------------------
def test_foreign_playlist_is_not_visible_or_modifiable():
    owner, other = _user(), _user()
    repository = _FakeRepository()
    playlist = repository.create(owner.id, "Privada")
    service, db, _ = _service(repository=repository)

    with pytest.raises(NotFoundError):
        service.get_playlist(other, playlist.id)
    with pytest.raises(NotFoundError):
        service.rename_playlist(other, playlist.id, PlaylistNameIn(name="Otra"))
    with pytest.raises(NotFoundError):
        service.delete_playlist(other, playlist.id, confirm=True)
    with pytest.raises(NotFoundError):
        service.add_track(other, playlist.id, PlaylistTrackAdd(track_id="t1"))
    with pytest.raises(NotFoundError):
        service.reorder_tracks(other, playlist.id, PlaylistReorder(playlist_track_ids=[]))

    assert db.rollbacks == 4  # get_playlist es lectura y no abre transacción


def test_delete_requires_confirmation_and_removes_the_playlist():
    user = _user()
    repository = _FakeRepository()
    playlist = repository.create(user.id, "Temporal")
    service, db, _ = _service(repository=repository)

    with pytest.raises(ConfirmationRequiredError):
        service.delete_playlist(user, playlist.id, confirm=False)
    assert repository.get_owned(playlist.id, user.id) is not None

    service.delete_playlist(user, playlist.id, confirm=True)

    assert repository.get_owned(playlist.id, user.id) is None
    assert db.commits == 1
    assert db.rollbacks == 1


def test_rename_validates_the_new_name():
    user = _user()
    repository = _FakeRepository()
    playlist = repository.create(user.id, "Original")
    service, db, _ = _service(repository=repository)

    with pytest.raises(ValidationFailedError):
        service.rename_playlist(user, playlist.id, PlaylistNameIn(name="   "))

    assert playlist.name == "Original"
    assert db.rollbacks == 1
