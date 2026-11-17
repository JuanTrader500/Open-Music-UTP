"""Endpoints REST de búsqueda y catálogo (RF-010, RF-011, RF-021)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Path, Query, Response, status
from sqlalchemy.orm import Session

from app.catalog.schemas import ArtistListResponse, GenreOut, SearchResponse, TrackOut
from app.catalog.service import CatalogService
from app.core.config import Settings, get_settings
from app.core.database import get_db

router = APIRouter(prefix="/catalog", tags=["catalog"])


def _service(db: Session, settings: Settings) -> CatalogService:
    """Construye el servicio con las dependencias de la petición."""
    return CatalogService(db, settings)


@router.get(
    "/search",
    response_model=SearchResponse,
    summary="Buscar canciones",
)
def search(
    q: str = Query(..., min_length=1, max_length=200, description="Texto a buscar"),
    limit: int = Query(default=20, ge=1, description="Máximo de resultados"),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> SearchResponse:
    """Busca en el proveedor, persiste y devuelve canciones embebibles (RF-010)."""
    return _service(db, settings).search(q, limit)


@router.get(
    "/tracks/{track_id}",
    response_model=TrackOut,
    summary="Detalle de una canción",
)
def get_track(
    track_id: str = Path(..., min_length=1, max_length=32),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> TrackOut:
    """Devuelve una canción o `404 TRACK_NOT_FOUND` (RF-010)."""
    return _service(db, settings).get_track(track_id)


@router.post(
    "/tracks/{track_id}/unplayable",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
    summary="Marcar una canción como no reproducible",
)
def mark_unplayable(
    track_id: str = Path(..., min_length=1, max_length=32),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> Response:
    """Marca una canción como no reproducible (RF-009, RN-012)."""
    _service(db, settings).mark_unplayable(track_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get(
    "/genres",
    response_model=list[GenreOut],
    summary="Listar géneros",
)
def list_genres(
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> list[GenreOut]:
    """Devuelve la lista cerrada de géneros (RF-011)."""
    return _service(db, settings).list_genres()


@router.get(
    "/artists",
    response_model=ArtistListResponse,
    summary="Listar artistas",
)
def list_artists(
    genre_ids: str | None = Query(
        default=None,
        description="Identificadores separados por comas, por ejemplo 1,2",
    ),
    q: str | None = Query(default=None, max_length=200, description="Filtro por nombre"),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> ArtistListResponse:
    """Lista artistas, opcionalmente filtrados por género y nombre (RF-021)."""
    return _service(db, settings).list_artists(
        genre_ids=genre_ids,
        query=q,
        limit=limit,
        offset=offset,
    )
