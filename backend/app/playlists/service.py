"""Fachada del módulo playlists (patrón Facade, entrega 2).

El router solo valida el contrato y llama aquí. La fachada coordina el
`PlaylistBuilder`, `CatalogService`, `PlaylistRepository` y los límites de
`Settings`; otros módulos no deben usar el repositorio directamente
(RF-013, RF-014, RF-015, RN-010).

Los métodos de escritura usan `@transactional`: la sesión se confirma o se
revierte en un solo lugar.
"""

from __future__ import annotations

import uuid

from sqlalchemy.orm import Session

from app.auth.models import User
from app.catalog.schemas import ArtistOut, GenreOut
from app.catalog.service import CatalogService
from app.core.config import Settings
from app.core.exceptions import (
    ConfirmationRequiredError,
    DuplicateTrackError,
    NotFoundError,
    PlaylistLimitError,
    TrackLimitError,
    ValidationFailedError,
)
from app.core.transactions import transactional
from app.playlists.builder import PlaylistBuilder
from app.playlists.models import Playlist
from app.playlists.repository import PlaylistRepository
from app.playlists.schemas import (
    PlaylistDetail,
    PlaylistListResponse,
    PlaylistNameIn,
    PlaylistReorder,
    PlaylistSummary,
    PlaylistTrackAdd,
    PlaylistTrackOut,
)


class PlaylistService:
    """Única puerta de entrada del módulo playlists."""

    def __init__(
        self,
        db: Session,
        settings: Settings,
        *,
        repository: PlaylistRepository | None = None,
        catalog: CatalogService | None = None,
    ) -> None:
        """Recibe la sesión, la configuración y las dependencias inyectables."""
        self.db = db
        self.settings = settings
        self.repository = repository or PlaylistRepository(db)
        self.catalog = catalog or CatalogService(db, settings)

    # ----------------------------------- Consultas -------------------------------------
    def list_playlists(self, user: User) -> PlaylistListResponse:
        """Lista las playlists del usuario autenticado (RF-013)."""
        rows = self.repository.list_for_user(user.id)
        items = [
            PlaylistSummary(
                id=playlist.id,
                name=playlist.name,
                track_count=track_count,
                created_at=playlist.created_at,
            )
            for playlist, track_count in rows
        ]
        return PlaylistListResponse(items=items, total=len(items))

    def get_playlist(self, user: User, playlist_id: uuid.UUID) -> PlaylistDetail:
        """Devuelve el detalle con pistas ordenadas o 404 si no es del usuario."""
        return self._detail(self._get_owned(user, playlist_id))

    # ----------------------------------- Escrituras ------------------------------------
    @transactional
    def create_playlist(self, user: User, data: PlaylistNameIn) -> PlaylistDetail:
        """Crea una playlist vacía respetando el máximo por usuario (RF-013)."""
        if self.repository.count_for_user(user.id) >= self.settings.max_playlists_per_user:
            raise PlaylistLimitError()
        name = self._validated_name(user, data.name)
        playlist = self.repository.create(user.id, name)
        return self._detail(playlist)

    @transactional
    def rename_playlist(
        self,
        user: User,
        playlist_id: uuid.UUID,
        data: PlaylistNameIn,
    ) -> PlaylistDetail:
        """Renombra una playlist del usuario (RF-015)."""
        playlist = self._get_owned(user, playlist_id)
        self.repository.rename(playlist, self._validated_name(user, data.name))
        return self._detail(playlist)

    @transactional
    def delete_playlist(
        self,
        user: User,
        playlist_id: uuid.UUID,
        *,
        confirm: bool,
    ) -> None:
        """Elimina la playlist con confirmación explícita (RF-015)."""
        playlist = self._get_owned(user, playlist_id)
        if not confirm:
            raise ConfirmationRequiredError()
        self.repository.delete(playlist)

    @transactional
    def add_track(
        self,
        user: User,
        playlist_id: uuid.UUID,
        data: PlaylistTrackAdd,
    ) -> PlaylistDetail:
        """Agrega una canción existente, validando duplicados y límite (RF-014)."""
        playlist = self._get_owned(user, playlist_id)
        track_id = data.track_id.strip()
        if not track_id:
            raise ValidationFailedError("El identificador de la pista es obligatorio.")

        self.catalog.get_track(track_id)

        current_track_ids = self.repository.list_track_ids(playlist.id)
        if track_id in current_track_ids and not data.confirm_duplicate:
            raise DuplicateTrackError()
        if len(current_track_ids) >= self.settings.max_tracks_per_playlist:
            raise TrackLimitError()

        builder = PlaylistBuilder.from_existing(
            str(user.id),
            name=playlist.name,
            track_ids=current_track_ids,
            max_name_length=self.settings.playlist_name_max_length,
            max_tracks=self.settings.max_tracks_per_playlist,
        )
        try:
            draft = builder.add_track(track_id).build()
        except ValueError as exc:
            raise ValidationFailedError(str(exc)) from exc

        self.repository.add_track(
            playlist.id,
            draft.track_ids[-1],
            self.repository.next_position(playlist.id),
        )
        return self._detail(playlist)

    @transactional
    def remove_track(
        self,
        user: User,
        playlist_id: uuid.UUID,
        playlist_track_id: int,
    ) -> None:
        """Quita una pista de la playlist y conserva posiciones consecutivas (RF-014)."""
        playlist = self._get_owned(user, playlist_id)
        playlist_track = self.repository.get_playlist_track(playlist.id, playlist_track_id)
        if playlist_track is None:
            raise NotFoundError("La pista no pertenece a la playlist.")
        self.repository.remove_track(playlist_track)

    @transactional
    def reorder_tracks(
        self,
        user: User,
        playlist_id: uuid.UUID,
        data: PlaylistReorder,
    ) -> PlaylistDetail:
        """Reordena de forma atómica con los ids actuales, sin faltantes ni repetidos (RF-015)."""
        playlist = self._get_owned(user, playlist_id)
        current_ids = self.repository.list_playlist_track_ids(playlist.id)
        requested = data.playlist_track_ids
        if (
            len(requested) != len(current_ids)
            or len(set(requested)) != len(requested)
            or set(requested) != set(current_ids)
        ):
            raise ValidationFailedError(
                "El orden debe incluir exactamente las pistas actuales, sin repetir."
            )
        self.repository.apply_order(playlist.id, requested)
        return self._detail(playlist)

    # ------------------------------------ Internos -------------------------------------
    def _get_owned(self, user: User, playlist_id: uuid.UUID) -> Playlist:
        """Devuelve la playlist del usuario o lanza 404 para no filtrar ajenas."""
        playlist = self.repository.get_owned(playlist_id, user.id)
        if playlist is None:
            raise NotFoundError("Playlist no encontrada.")
        return playlist

    def _validated_name(self, user: User, name: str) -> str:
        """Valida el nombre con el Builder y traduce `ValueError` a 422."""
        builder = PlaylistBuilder(
            str(user.id),
            max_name_length=self.settings.playlist_name_max_length,
            max_tracks=self.settings.max_tracks_per_playlist,
        )
        try:
            return builder.with_name(name).build().name
        except ValueError as exc:
            raise ValidationFailedError(str(exc)) from exc

    def _detail(self, playlist: Playlist) -> PlaylistDetail:
        """Arma el detalle con los metadatos de catálogo ya unidos por el repositorio."""
        rows = self.repository.list_tracks_with_metadata(playlist.id)
        tracks = [
            PlaylistTrackOut(
                playlist_track_id=playlist_track.id,
                position=playlist_track.position,
                track_id=track.track_id,
                title=track.title,
                artist=ArtistOut.model_validate(artist),
                genre=GenreOut.model_validate(genre),
                duration_s=track.duration_s,
                view_count=track.view_count,
                like_count=track.like_count,
                thumbnail_url=track.thumbnail_url,
                is_embeddable=track.is_embeddable,
            )
            for playlist_track, track, artist, genre in rows
        ]
        return PlaylistDetail(
            id=playlist.id,
            name=playlist.name,
            created_at=playlist.created_at,
            tracks=tracks,
            total=len(tracks),
        )
