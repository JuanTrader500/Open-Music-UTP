"""Pruebas de los datos base del catálogo (RF-011, RF-021)."""

from __future__ import annotations

from sqlalchemy import func, select

from app.catalog.models import Artist, Genre
from app.catalog.repository import CatalogRepository
from app.catalog.seed_data import ARTISTS, GENRES
from app.catalog.seed_importer import ensure_base_catalog


def test_lista_cerrada_de_generos():
    codes = [code for code, _ in GENRES]

    assert len(GENRES) == 45
    assert len(set(codes)) == 45
    assert "sin_clasificar" in codes


def test_lista_editorial_de_artistas_es_unica():
    normalized = [name.strip().lower() for name in ARTISTS]

    assert len(ARTISTS) == 440
    assert len(set(normalized)) == 440


def test_asegurar_base_es_idempotente(db_session):
    repository = CatalogRepository(db_session)

    ensure_base_catalog(repository)
    ensure_base_catalog(repository)

    genres = db_session.scalar(select(func.count()).select_from(Genre))
    artists = db_session.scalar(select(func.count()).select_from(Artist))
    assert genres == 45
    assert artists == 440
    unclassified = repository.get_genre_by_code("sin_clasificar")
    assert unclassified is not None
    assert unclassified.name == "Sin clasificar"
