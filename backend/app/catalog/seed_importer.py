"""Importación de playlists semilla del catálogo (RF-011).

Uso:
    python -m app.catalog.seed_importer --all
    python -m app.catalog.seed_importer --playlist PL_SIM_ROCK --genre rock

La operación es idempotente: actualiza las semillas y las canciones existentes
sin duplicarlas. En una base limpia deja el catálogo listo para la demo con el
proveedor simulado.
"""

from __future__ import annotations

import argparse
import logging
from collections.abc import Sequence

from app.catalog.repository import CatalogRepository
from app.catalog.seed_data import ARTISTS, GENRES
from app.catalog.service import CatalogService
from app.core.config import get_settings
from app.core.database import SessionLocal, get_engine

logger = logging.getLogger(__name__)

#: Playlists semilla del proveedor simulado y el género que representan.
SEED_PLAYLISTS: dict[str, str] = {
    "PL_SIM_ROCK": "rock",
    "PL_SIM_POP": "pop",
    "PL_SIM_SALSA": "salsa",
}


def ensure_base_catalog(repository: CatalogRepository) -> None:
    """Asegura los 45 géneros y 440 artistas del esquema v6 (RF-011, RF-021)."""
    for code, name in GENRES:
        repository.upsert_genre(code, name)
    for name in ARTISTS:
        repository.get_or_create_artist(name)


def import_all(service: CatalogService) -> dict[str, int]:
    """Importa todas las playlists semilla conocidas."""
    return {
        playlist_id: service.import_seed(playlist_id, genre_code)
        for playlist_id, genre_code in SEED_PLAYLISTS.items()
    }


def build_parser() -> argparse.ArgumentParser:
    """Construye el parser de línea de comandos."""
    parser = argparse.ArgumentParser(
        description="Importa playlists semilla al catálogo (RF-011).",
    )
    parser.add_argument("--all", action="store_true", help="Importa todas las semillas.")
    parser.add_argument("--playlist", help="Identificador de una playlist semilla.")
    parser.add_argument("--genre", help="Código de género de la playlist indicada.")
    parser.add_argument(
        "--max-items",
        type=int,
        default=None,
        help="Máximo de canciones a importar por playlist.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Ejecuta la importación y devuelve el código de salida del proceso."""
    args = build_parser().parse_args(argv)
    if not args.all and not (args.playlist and args.genre):
        build_parser().error("Indica --all o --playlist junto con --genre.")

    logging.basicConfig(level=logging.INFO, format="%(message)s")
    settings = get_settings()
    session = SessionLocal(bind=get_engine())
    try:
        repository = CatalogRepository(session)
        ensure_base_catalog(repository)
        session.commit()
        logger.info("Base: %s géneros y %s artistas", len(GENRES), len(ARTISTS))

        service = CatalogService(session, settings)
        if args.all:
            results = import_all(service)
        else:
            results = {
                args.playlist: service.import_seed(
                    args.playlist,
                    args.genre,
                    max_items=args.max_items,
                )
            }
        for playlist_id, count in results.items():
            logger.info("%s: %s canciones importadas", playlist_id, count)
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
