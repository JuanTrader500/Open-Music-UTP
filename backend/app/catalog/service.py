"""Lógica del catálogo: proveedor, persistencia y consultas (RF-010, RF-011).

El router no conoce el proveedor ni el ORM. Este servicio valida la consulta,
llama al proveedor configurado, persiste artistas/canciones/género y arma los
contratos de salida.
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.catalog.genres import UNCLASSIFIED_CODE, resolve_genre
from app.catalog.models import Artist, Genre, Track
from app.catalog.providers.base import validate_query
from app.catalog.providers.models import TrackMetadata
from app.catalog.providers.music_provider import MusicProvider
from app.catalog.providers.registry import build_provider_factory
from app.catalog.repository import CatalogRepository
from app.catalog.schemas import (
    ArtistListResponse,
    ArtistOut,
    GenreOut,
    SearchResponse,
    TrackOut,
)
from app.core.config import Settings
from app.core.exceptions import (
    ConfigurationError,
    TrackNotFoundError,
    ValidationFailedError,
)


class CatalogService:
    """Única puerta de entrada del módulo catálogo."""

    def __init__(
        self,
        db: Session,
        settings: Settings,
        *,
        provider: MusicProvider | None = None,
        repository: CatalogRepository | None = None,
    ) -> None:
        """Recibe la sesión, la configuración y las dependencias inyectables."""
        self.db = db
        self.settings = settings
        self.repository = repository or CatalogRepository(db)
        self.provider = provider or MusicProvider(build_provider_factory(settings))

    def search(self, query: str, limit: int) -> SearchResponse:
        """Busca canciones, las persiste y devuelve solo las embebibles (RF-010)."""
        cleaned = validate_query(query, self.settings.search_min_chars)
        if limit > self.settings.youtube_max_results:
            raise ValidationFailedError(
                f"El límite no puede superar {self.settings.youtube_max_results}."
            )

        tracks = self.provider.search_tracks(cleaned, limit)
        try:
            for track in tracks:
                self._persist_track(track)
            self.db.commit()
        except Exception:
            self.db.rollback()
            raise

        views = self.repository.get_track_views([track.track_id for track in tracks])
        items: list[TrackOut] = []
        for track in tracks:
            view = views.get(track.track_id)
            if view is None or not view[0].is_embeddable:
                continue
            items.append(self._to_track_out(*view))
        return SearchResponse(items=items, total=len(items), query=cleaned)

    def get_track(self, track_id: str) -> TrackOut:
        """Devuelve el detalle de una canción o lanza `TRACK_NOT_FOUND`."""
        view = self.repository.get_track_view(track_id)
        if view is None:
            raise TrackNotFoundError()
        return self._to_track_out(*view)

    def mark_unplayable(self, track_id: str) -> None:
        """Marca una canción como no reproducible (RF-009, RN-012)."""
        try:
            if not self.repository.mark_unplayable(track_id):
                raise TrackNotFoundError()
            self.db.commit()
        except Exception:
            self.db.rollback()
            raise

    def list_genres(self) -> list[GenreOut]:
        """Lista los géneros de la lista cerrada (RF-011)."""
        return [GenreOut.model_validate(genre) for genre in self.repository.list_genres()]

    def list_artists(
        self,
        *,
        genre_ids: str | None,
        query: str | None,
        limit: int,
        offset: int,
    ) -> ArtistListResponse:
        """Lista artistas, filtrando por géneros y nombre si se indican (RF-021)."""
        parsed_genres = self._parse_genre_ids(genre_ids)
        cleaned_query = query.strip() if query and query.strip() else None
        artists = self.repository.list_artists(
            genre_ids=parsed_genres,
            query=cleaned_query,
            limit=limit,
            offset=offset,
        )
        total = self.repository.count_artists(
            genre_ids=parsed_genres,
            query=cleaned_query,
        )
        return ArtistListResponse(
            items=[ArtistOut.model_validate(artist) for artist in artists],
            total=total,
            limit=limit,
            offset=offset,
        )

    def import_seed(
        self,
        playlist_id: str,
        genre_code: str,
        *,
        max_items: int | None = None,
    ) -> int:
        """Importa una playlist semilla y le asigna un género (RF-011)."""
        genre = self.repository.get_genre_by_code(genre_code)
        if genre is None:
            raise ValidationFailedError(f"El género {genre_code!r} no existe.")
        limit = max_items if max_items is not None else self.settings.youtube_max_results
        tracks = self.provider.import_playlist(playlist_id, limit)
        try:
            self.repository.upsert_genre_seed(playlist_id, genre.id)
            for track in tracks:
                self._persist_track(track, seed_genre=genre, preserve_unplayable=False)
            self.db.commit()
        except Exception:
            self.db.rollback()
            raise
        return len(tracks)

    def _persist_track(
        self,
        metadata: TrackMetadata,
        *,
        seed_genre: Genre | None = None,
        preserve_unplayable: bool = True,
    ) -> Track:
        """Inserta o actualiza una canción resolviendo su género."""
        artist = self.repository.get_or_create_artist(metadata.channel_title)
        if seed_genre is not None:
            genre_id = seed_genre.id
            genre_source = "seed"
        else:
            existing = self.repository.get_track(metadata.track_id)
            if existing is not None and existing.genre_source == "seed":
                genre_id = existing.genre_id
                genre_source = existing.genre_source
            else:
                unclassified = self._unclassified_genre()
                category_genre_id = (
                    existing.genre_id
                    if existing is not None and existing.genre_source == "youtube_category"
                    else None
                )
                resolution = resolve_genre(
                    seed_genre_id=None,
                    artist_genre_id=self.repository.get_artist_genre_id(artist.id),
                    category_genre_id=category_genre_id,
                    unclassified_genre_id=unclassified.id,
                )
                genre_id = resolution.genre_id
                genre_source = resolution.source

        return self.repository.upsert_track(
            track_id=metadata.track_id,
            title=metadata.title,
            artist_id=artist.id,
            genre_id=genre_id,
            genre_source=genre_source,
            duration_s=metadata.duration_s,
            view_count=metadata.view_count,
            like_count=metadata.like_count,
            thumbnail_url=metadata.thumbnail_url or "",
            is_embeddable=metadata.is_embeddable,
            preserve_unplayable=preserve_unplayable,
        )

    def _unclassified_genre(self) -> Genre:
        """Devuelve el género comodín o falla si la base no está sembrada."""
        genre = self.repository.get_genre_by_code(UNCLASSIFIED_CODE)
        if genre is None:
            raise ConfigurationError(f"Falta el género {UNCLASSIFIED_CODE!r} en la base de datos.")
        return genre

    @staticmethod
    def _parse_genre_ids(raw: str | None) -> list[int]:
        """Convierte `'1,2,3'` en una lista de identificadores positivos."""
        if not raw or not raw.strip():
            return []
        try:
            genre_ids = [int(part.strip()) for part in raw.split(",") if part.strip()]
        except ValueError as exc:
            raise ValidationFailedError(
                "genre_ids debe ser una lista de enteros separada por comas."
            ) from exc
        if any(genre_id <= 0 for genre_id in genre_ids):
            raise ValidationFailedError("Los identificadores de género deben ser positivos.")
        return genre_ids

    @staticmethod
    def _to_track_out(track: Track, artist: Artist, genre: Genre) -> TrackOut:
        """Arma el contrato de salida de una canción."""
        return TrackOut(
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
