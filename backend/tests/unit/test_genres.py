"""Pruebas de la resolución de género del catálogo (RF-011, RN-009)."""

from __future__ import annotations

from app.catalog.genres import normalize_artist_name, resolve_genre


def test_prioridad_semilla_sobre_las_demas_fuentes():
    resolution = resolve_genre(
        seed_genre_id=10,
        artist_genre_id=20,
        category_genre_id=30,
        unclassified_genre_id=45,
    )

    assert resolution.genre_id == 10
    assert resolution.source == "seed"


def test_prioridad_artista_sobre_categoria():
    resolution = resolve_genre(
        seed_genre_id=None,
        artist_genre_id=20,
        category_genre_id=30,
        unclassified_genre_id=45,
    )

    assert resolution.genre_id == 20
    assert resolution.source == "artist"


def test_prioridad_categoria_sobre_sin_clasificar():
    resolution = resolve_genre(
        seed_genre_id=None,
        artist_genre_id=None,
        category_genre_id=30,
        unclassified_genre_id=45,
    )

    assert resolution.genre_id == 30
    assert resolution.source == "youtube_category"


def test_sin_fuentes_usa_sin_clasificar():
    resolution = resolve_genre(
        seed_genre_id=None,
        artist_genre_id=None,
        category_genre_id=None,
        unclassified_genre_id=45,
    )

    assert resolution.genre_id == 45
    assert resolution.source == "unclassified"


def test_normalizacion_de_artista():
    assert normalize_artist_name("  Los Cafeteros Eléctricos  ") == "los cafeteros eléctricos"
