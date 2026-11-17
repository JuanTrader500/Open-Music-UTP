"""Acceso a datos de playlists y sus pistas (RF-013 a RF-015, RN-010).

El repositorio no hace `commit`: la transacción la controla el servicio con
`@transactional`. Todas las consultas usan SQLAlchemy 2.0 y devuelven entidades
ORM o tuplas internas.
"""

from __future__ import annotations

import uuid
from collections.abc import Sequence

from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from app.catalog.models import Artist, Genre, Track
from app.playlists.models import Playlist, PlaylistTrack


class PlaylistRepository:
    """Consultas y escrituras de `playlists` y `playlist_tracks`."""

    def __init__(self, db: Session) -> None:
        """Guarda la sesión de base de datos de la petición."""
        self.db = db

    # ----------------------------------- Playlists -------------------------------------
    def count_for_user(self, user_id: uuid.UUID) -> int:
        """Cuenta las playlists del usuario (RN-010)."""
        total = self.db.scalar(
            select(func.count()).select_from(Playlist).where(Playlist.user_id == user_id)
        )
        return int(total or 0)

    def list_for_user(self, user_id: uuid.UUID) -> list[tuple[Playlist, int]]:
        """Lista las playlists del usuario con el número de pistas de cada una."""
        statement = (
            select(Playlist, func.count(PlaylistTrack.id))
            .outerjoin(PlaylistTrack, PlaylistTrack.playlist_id == Playlist.id)
            .where(Playlist.user_id == user_id)
            .group_by(Playlist.id)
            .order_by(Playlist.created_at.desc(), Playlist.name)
        )
        return list(self.db.execute(statement).all())

    def get_owned(self, playlist_id: uuid.UUID, user_id: uuid.UUID) -> Playlist | None:
        """Devuelve la playlist solo si pertenece al usuario autenticado."""
        return self.db.scalar(
            select(Playlist).where(
                Playlist.id == playlist_id,
                Playlist.user_id == user_id,
            )
        )

    def create(self, user_id: uuid.UUID, name: str) -> Playlist:
        """Inserta una playlist vacía y devuelve la entidad con sus valores por defecto."""
        playlist = Playlist(user_id=user_id, name=name)
        self.db.add(playlist)
        self.db.flush()
        self.db.refresh(playlist)
        return playlist

    def rename(self, playlist: Playlist, name: str) -> None:
        """Cambia el nombre de una playlist ya validada."""
        playlist.name = name
        self.db.flush()

    def delete(self, playlist: Playlist) -> None:
        """Elimina la playlist; la cascada borra sus pistas, no las del catálogo."""
        self.db.delete(playlist)
        self.db.flush()

    # ------------------------------------ Pistas ---------------------------------------
    def list_playlist_track_ids(self, playlist_id: uuid.UUID) -> list[int]:
        """Devuelve los `playlist_track_id` en el orden actual."""
        statement = (
            select(PlaylistTrack.id)
            .where(PlaylistTrack.playlist_id == playlist_id)
            .order_by(PlaylistTrack.position)
        )
        return list(self.db.scalars(statement).all())

    def list_track_ids(self, playlist_id: uuid.UUID) -> list[str]:
        """Devuelve los `track_id` de la playlist en orden."""
        statement = (
            select(PlaylistTrack.track_id)
            .where(PlaylistTrack.playlist_id == playlist_id)
            .order_by(PlaylistTrack.position)
        )
        return list(self.db.scalars(statement).all())

    def has_track(self, playlist_id: uuid.UUID, track_id: str) -> bool:
        """Indica si la canción ya está en la playlist (RF-014)."""
        found = self.db.scalar(
            select(PlaylistTrack.id)
            .where(
                PlaylistTrack.playlist_id == playlist_id,
                PlaylistTrack.track_id == track_id,
            )
            .limit(1)
        )
        return found is not None

    def next_position(self, playlist_id: uuid.UUID) -> int:
        """Devuelve la siguiente posición consecutiva (1..n)."""
        last = self.db.scalar(
            select(func.max(PlaylistTrack.position)).where(PlaylistTrack.playlist_id == playlist_id)
        )
        return int(last or 0) + 1

    def add_track(self, playlist_id: uuid.UUID, track_id: str, position: int) -> PlaylistTrack:
        """Agrega una canción al final de la playlist."""
        playlist_track = PlaylistTrack(
            playlist_id=playlist_id,
            track_id=track_id,
            position=position,
        )
        self.db.add(playlist_track)
        self.db.flush()
        return playlist_track

    def get_playlist_track(
        self,
        playlist_id: uuid.UUID,
        playlist_track_id: int,
    ) -> PlaylistTrack | None:
        """Busca una pista dentro de una playlist concreta."""
        return self.db.scalar(
            select(PlaylistTrack).where(
                PlaylistTrack.id == playlist_track_id,
                PlaylistTrack.playlist_id == playlist_id,
            )
        )

    def remove_track(self, playlist_track: PlaylistTrack) -> None:
        """Quita una pista y recorre las posiciones siguientes para no dejar huecos."""
        playlist_id = playlist_track.playlist_id
        removed_position = playlist_track.position
        self.db.delete(playlist_track)
        self.db.flush()
        self.db.execute(
            update(PlaylistTrack)
            .where(
                PlaylistTrack.playlist_id == playlist_id,
                PlaylistTrack.position > removed_position,
            )
            .values(position=PlaylistTrack.position - 1)
            .execution_options(synchronize_session=False)
        )

    def apply_order(self, playlist_id: uuid.UUID, ordered_ids: Sequence[int]) -> None:
        """Escribe las posiciones 1..n en una sola transacción.

        El constraint único `(playlist_id, position)` es diferido, así que se
        pueden intercambiar posiciones sin conflictos intermedios (RF-015).
        """
        for position, playlist_track_id in enumerate(ordered_ids, start=1):
            self.db.execute(
                update(PlaylistTrack)
                .where(
                    PlaylistTrack.id == playlist_track_id,
                    PlaylistTrack.playlist_id == playlist_id,
                )
                .values(position=position)
                .execution_options(synchronize_session=False)
            )

    def list_tracks_with_metadata(
        self,
        playlist_id: uuid.UUID,
    ) -> list[tuple[PlaylistTrack, Track, Artist, Genre]]:
        """Devuelve las pistas de la playlist con canción, artista y género."""
        statement = (
            select(PlaylistTrack, Track, Artist, Genre)
            .join(Track, Track.track_id == PlaylistTrack.track_id)
            .join(Artist, Artist.id == Track.artist_id)
            .join(Genre, Genre.id == Track.genre_id)
            .where(PlaylistTrack.playlist_id == playlist_id)
            .order_by(PlaylistTrack.position)
        )
        return list(self.db.execute(statement).all())
