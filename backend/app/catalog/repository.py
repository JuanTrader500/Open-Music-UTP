"""Acceso a datos del catálogo (RF-010, RF-011, RF-021).

El repositorio no hace `commit`: la transacción la controla el servicio. Todas
las consultas usan SQLAlchemy 2.0 y devuelven entidades ORM o tuplas internas.
"""

from __future__ import annotations

from collections.abc import Sequence

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.catalog.models import Artist, Genre, GenreSeed, Track


class CatalogRepository:
    """Consultas y escrituras de las tablas del catálogo."""

    def __init__(self, db: Session) -> None:
        """Guarda la sesión de base de datos de la petición."""
        self.db = db

    def get_genre_by_code(self, code: str) -> Genre | None:
        """Busca un género por su código estable."""
        return self.db.scalar(select(Genre).where(Genre.code == code))

    def get_genre_by_id(self, genre_id: int) -> Genre | None:
        """Busca un género por su identificador."""
        return self.db.get(Genre, genre_id)

    def upsert_genre(self, code: str, name: str) -> Genre:
        """Asegura un género de la lista cerrada sin duplicarlo."""
        genre = self.get_genre_by_code(code)
        if genre is None:
            genre = Genre(code=code, name=name)
            self.db.add(genre)
        elif genre.name != name:
            genre.name = name
        self.db.flush()
        return genre

    def list_genres(self) -> list[Genre]:
        """Lista todos los géneros ordenados por nombre."""
        return list(self.db.scalars(select(Genre).order_by(Genre.name)).all())

    def get_or_create_artist(self, name: str) -> Artist:
        """Devuelve el artista por nombre normalizado o lo crea (RF-010)."""
        cleaned = name.strip() or "Artista desconocido"
        normalized = cleaned.lower()
        artist = self.db.scalar(select(Artist).where(Artist.name_normalized == normalized))
        if artist is not None:
            return artist
        artist = Artist(name=cleaned, name_normalized=normalized)
        self.db.add(artist)
        self.db.flush()
        return artist

    def get_artist_genre_id(self, artist_id: int) -> int | None:
        """Infiere el género de un artista desde sus canciones ya clasificadas."""
        return self.db.scalar(
            select(Track.genre_id)
            .where(
                Track.artist_id == artist_id,
                Track.genre_source != "unclassified",
            )
            .order_by(Track.updated_at.desc())
            .limit(1)
        )

    def get_track(self, track_id: str) -> Track | None:
        """Busca una canción por su identificador."""
        return self.db.get(Track, track_id)

    def upsert_track(
        self,
        *,
        track_id: str,
        title: str,
        artist_id: int,
        genre_id: int,
        genre_source: str,
        duration_s: int,
        view_count: int,
        like_count: int,
        thumbnail_url: str,
        is_embeddable: bool,
        preserve_unplayable: bool = True,
    ) -> Track:
        """Inserta o actualiza una canción sin duplicar su `track_id`.

        Si `preserve_unplayable` es verdadero, una canción marcada como no
        reproducible por C-03 no vuelve a habilitarse en una búsqueda posterior.
        La importación de semillas pasa `False` para restaurar el catálogo.
        """
        track = self.db.get(Track, track_id)
        if track is None:
            track = Track(
                track_id=track_id,
                title=title,
                artist_id=artist_id,
                genre_id=genre_id,
                genre_source=genre_source,
                duration_s=duration_s,
                view_count=view_count,
                like_count=like_count,
                thumbnail_url=thumbnail_url,
                is_embeddable=is_embeddable,
            )
            self.db.add(track)
        else:
            track.title = title
            track.artist_id = artist_id
            track.genre_id = genre_id
            track.genre_source = genre_source
            track.duration_s = duration_s
            track.view_count = view_count
            track.like_count = like_count
            track.thumbnail_url = thumbnail_url
            if track.is_embeddable or not preserve_unplayable:
                track.is_embeddable = is_embeddable
            track.updated_at = func.now()
        self.db.flush()
        return track

    def mark_unplayable(self, track_id: str) -> bool:
        """Marca una canción como no reproducible (RF-009, RN-012)."""
        track = self.db.get(Track, track_id)
        if track is None:
            return False
        track.is_embeddable = False
        track.updated_at = func.now()
        self.db.flush()
        return True

    def get_track_view(self, track_id: str) -> tuple[Track, Artist, Genre] | None:
        """Devuelve canción, artista y género en una sola consulta."""
        row = self.db.execute(
            select(Track, Artist, Genre)
            .join(Artist, Track.artist_id == Artist.id)
            .join(Genre, Track.genre_id == Genre.id)
            .where(Track.track_id == track_id)
        ).first()
        if row is None:
            return None
        return row[0], row[1], row[2]

    def get_track_views(self, track_ids: Sequence[str]) -> dict[str, tuple[Track, Artist, Genre]]:
        """Devuelve las vistas de varias canciones indexadas por `track_id`."""
        if not track_ids:
            return {}
        rows = self.db.execute(
            select(Track, Artist, Genre)
            .join(Artist, Track.artist_id == Artist.id)
            .join(Genre, Track.genre_id == Genre.id)
            .where(Track.track_id.in_(list(track_ids)))
        ).all()
        return {track.track_id: (track, artist, genre) for track, artist, genre in rows}

    def upsert_genre_seed(self, playlist_id: str, genre_id: int) -> GenreSeed:
        """Asocia una playlist semilla con un género (RF-011)."""
        seed = self.db.get(GenreSeed, playlist_id)
        if seed is None:
            seed = GenreSeed(playlist_id=playlist_id, genre_id=genre_id)
            self.db.add(seed)
        else:
            seed.genre_id = genre_id
        self.db.flush()
        return seed

    def list_artists(
        self,
        *,
        genre_ids: Sequence[int],
        query: str | None,
        limit: int,
        offset: int,
    ) -> list[Artist]:
        """Lista artistas, opcionalmente filtrados por género y nombre (RF-021)."""
        statement = select(Artist)
        if genre_ids:
            statement = (
                statement.join(Track, Track.artist_id == Artist.id)
                .where(Track.genre_id.in_(list(genre_ids)))
                .distinct()
            )
        if query:
            statement = statement.where(Artist.name_normalized.contains(query.lower()))
        statement = statement.order_by(Artist.name).limit(limit).offset(offset)
        return list(self.db.scalars(statement).all())

    def count_artists(self, *, genre_ids: Sequence[int], query: str | None) -> int:
        """Cuenta los artistas que cumplen los filtros del listado."""
        statement = select(func.count(func.distinct(Artist.id))).select_from(Artist)
        if genre_ids:
            statement = statement.join(Track, Track.artist_id == Artist.id).where(
                Track.genre_id.in_(list(genre_ids))
            )
        if query:
            statement = statement.where(Artist.name_normalized.contains(query.lower()))
        return int(self.db.scalar(statement) or 0)
