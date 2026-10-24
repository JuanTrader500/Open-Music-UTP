"""Builder para crear playlists (RF-013, RF-015, RN-010).

Construcción por pasos con validación incremental: nombre, agregar pistas y
reordenar. Evita constructores telescópicos y garantiza objetos `Playlist`
siempre válidos. Los límites llegan como parámetros desde la configuración; el
Builder no conoce `Settings`. El error de validación es `ValueError` y el
servicio lo traduce a `ValidationFailedError`.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Playlist:
    """Playlist inmutable creada por el Builder."""

    owner_id: str
    name: str
    track_ids: tuple[str, ...] = ()

    def reordered(self, from_index: int, to_index: int) -> Playlist:
        """RF-015: devuelve una copia con una pista movida de posición."""
        tracks = list(self.track_ids)
        track = tracks.pop(from_index)
        tracks.insert(to_index, track)
        return Playlist(owner_id=self.owner_id, name=self.name, track_ids=tuple(tracks))


class PlaylistBuilder:
    """Builder fluido de `Playlist` con límites recibidos desde la configuración."""

    def __init__(self, owner_id: str, *, max_name_length: int, max_tracks: int) -> None:
        """Guarda el propietario y los límites de nombre y de pistas."""
        if not owner_id.strip():
            raise ValueError("El propietario de la playlist es obligatorio.")
        self._owner_id = owner_id.strip()
        self._max_name_length = max_name_length
        self._max_tracks = max_tracks
        self._name = ""
        self._track_ids: list[str] = []

    def with_name(self, name: str) -> PlaylistBuilder:
        """RF-013: asigna un nombre de entre 1 y `max_name_length` caracteres."""
        cleaned = name.strip()
        if not cleaned:
            raise ValueError("El nombre de la playlist es obligatorio (RF-013).")
        if len(cleaned) > self._max_name_length:
            raise ValueError(f"El nombre supera {self._max_name_length} caracteres (RF-013).")
        self._name = cleaned
        return self

    def add_track(self, track_id: str) -> PlaylistBuilder:
        """Agrega una pista al final si no se supera el máximo (RN-010)."""
        cleaned = track_id.strip()
        if not cleaned:
            raise ValueError("El identificador de la pista es obligatorio.")
        if len(self._track_ids) >= self._max_tracks:
            raise ValueError(f"Máximo {self._max_tracks} pistas por playlist (RN-010).")
        self._track_ids.append(cleaned)
        return self

    def build(self) -> Playlist:
        """Devuelve la `Playlist`; exige que el nombre esté definido."""
        if not self._name:
            raise ValueError("Falta el nombre: llama with_name() antes de build().")
        return Playlist(
            owner_id=self._owner_id,
            name=self._name,
            track_ids=tuple(self._track_ids),
        )
