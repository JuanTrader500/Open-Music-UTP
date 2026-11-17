"""Endpoints REST de playlists (RF-013, RF-014, RF-015, RN-010)."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Path, Query, Response, status
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.auth.models import User
from app.core.config import Settings, get_settings
from app.core.database import get_db
from app.playlists.schemas import (
    PlaylistDetail,
    PlaylistListResponse,
    PlaylistNameIn,
    PlaylistReorder,
    PlaylistTrackAdd,
)
from app.playlists.service import PlaylistService

router = APIRouter(prefix="/playlists", tags=["playlists"])


def _service(db: Session, settings: Settings) -> PlaylistService:
    """Construye la fachada con las dependencias de la petición."""
    return PlaylistService(db, settings)


@router.get(
    "",
    response_model=PlaylistListResponse,
    summary="Listar playlists",
)
def list_playlists(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> PlaylistListResponse:
    """Lista solo las playlists del usuario autenticado (RF-013)."""
    return _service(db, settings).list_playlists(user)


@router.post(
    "",
    response_model=PlaylistDetail,
    status_code=status.HTTP_201_CREATED,
    summary="Crear playlist",
)
def create_playlist(
    payload: PlaylistNameIn,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> PlaylistDetail:
    """Crea una playlist vacía; 422 si el nombre es inválido (RF-013)."""
    return _service(db, settings).create_playlist(user, payload)


@router.get(
    "/{playlist_id}",
    response_model=PlaylistDetail,
    summary="Ver detalle de una playlist",
)
def get_playlist(
    playlist_id: UUID = Path(...),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> PlaylistDetail:
    """Devuelve pistas ordenadas con `playlist_track_id` y `position` (RF-013)."""
    return _service(db, settings).get_playlist(user, playlist_id)


@router.patch(
    "/{playlist_id}",
    response_model=PlaylistDetail,
    summary="Renombrar playlist",
)
def rename_playlist(
    payload: PlaylistNameIn,
    playlist_id: UUID = Path(...),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> PlaylistDetail:
    """Renombra una playlist; 422 si el nombre es inválido (RF-015)."""
    return _service(db, settings).rename_playlist(user, playlist_id, payload)


@router.delete(
    "/{playlist_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
    summary="Eliminar playlist",
)
def delete_playlist(
    playlist_id: UUID = Path(...),
    confirm: bool = Query(default=False, description="Debe ser true para eliminar"),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> Response:
    """Elimina la playlist con `?confirm=true`; 409 sin confirmación (RF-015)."""
    _service(db, settings).delete_playlist(user, playlist_id, confirm=confirm)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/{playlist_id}/tracks",
    response_model=PlaylistDetail,
    status_code=status.HTTP_201_CREATED,
    summary="Agregar canción a una playlist",
)
def add_track(
    payload: PlaylistTrackAdd,
    playlist_id: UUID = Path(...),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> PlaylistDetail:
    """Agrega una canción; 404 si no existe y 409 si duplica sin confirmar (RF-014)."""
    return _service(db, settings).add_track(user, playlist_id, payload)


@router.put(
    "/{playlist_id}/tracks/order",
    response_model=PlaylistDetail,
    summary="Reordenar canciones",
)
def reorder_tracks(
    payload: PlaylistReorder,
    playlist_id: UUID = Path(...),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> PlaylistDetail:
    """Reordena con todos los ids actuales una sola vez; 422 si no coinciden (RF-015)."""
    return _service(db, settings).reorder_tracks(user, playlist_id, payload)


@router.delete(
    "/{playlist_id}/tracks/{playlist_track_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
    summary="Quitar canción de una playlist",
)
def remove_track(
    playlist_id: UUID = Path(...),
    playlist_track_id: int = Path(..., ge=1),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> Response:
    """Quita una pista de la playlist; 404 si no pertenece a ella (RF-014)."""
    _service(db, settings).remove_track(user, playlist_id, playlist_track_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
