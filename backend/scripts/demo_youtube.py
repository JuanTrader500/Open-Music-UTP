"""Demo para la sustentación: usa el Abstract Factory desde la línea de comandos.

Ejemplos (desde la carpeta backend/):
    python -m scripts.demo_youtube --provider simulated search rock
    python -m scripts.demo_youtube --provider youtube search "salsa clasica"
    python -m scripts.demo_youtube --provider youtube playlist PLxxxxxxxx
"""

from __future__ import annotations

import argparse

from app.catalog.providers.music_provider import MusicProvider
from app.catalog.providers.registry import build_provider_factory
from app.core.config import Settings
from app.core.exceptions import MusicAppError


def _print_tracks(tracks) -> None:
    if not tracks:
        print("Sin resultados.")
    for i, t in enumerate(tracks, start=1):
        mins, secs = divmod(t.duration_s, 60)
        print(
            f"{i:>2}. {t.title} — {t.channel_title} [{mins}:{secs:02d}] "
            f"({t.view_count:,} vistas) id={t.track_id}"
        )


def main() -> None:
    parser = argparse.ArgumentParser(description="Demo del proveedor de música")
    parser.add_argument("--provider", choices=["youtube", "simulated"], default=None)
    sub = parser.add_subparsers(dest="command", required=True)
    p_search = sub.add_parser("search", help="Buscar canciones")
    p_search.add_argument("query")
    p_playlist = sub.add_parser("playlist", help="Importar una playlist semilla")
    p_playlist.add_argument("playlist_id")
    args = parser.parse_args()

    settings = Settings.from_env()
    if args.provider:
        settings = settings.model_copy(update={"music_provider": args.provider})

    try:
        factory = build_provider_factory(settings)  # fábrica concreta elegida
        provider = MusicProvider(factory)  # el cliente solo ve la abstracta
        print(f"Proveedor activo: {factory.name} ({type(factory).__name__})\n")
        if args.command == "search":
            _print_tracks(provider.search_tracks(args.query))
        else:
            _print_tracks(provider.import_playlist(args.playlist_id))
    except MusicAppError as exc:
        print(f"Error: {exc}")


if __name__ == "__main__":
    main()
