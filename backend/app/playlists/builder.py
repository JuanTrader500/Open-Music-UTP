"""Builder para RF-013 Crear playlist (ESC-02).

Construcción por pasos con validación incremental (RN-002/003/010):
nombre → descripción → agregar pistas → favorita → build().
Evita constructor telescópico y garantiza objetos Playlist siempre válidos.
"""
from __future__ import annotations

from dataclasses import dataclass

MAX_TRACKS = 500  # RN-010: tope razonable antes de TBD de persistencia
MAX_NAME_LEN = 100


@dataclass(frozen=True)
class Playlist:
    owner_id: str
    name: str
    description: str = ""
    track_ids: tuple[str, ...] = ()
    is_favorite: bool = False

    def reordered(self, from_index: int, to_index: int) -> "Playlist":
        """RN-003: el orden es propio del usuario; devuelve nueva instancia."""
        tracks = list(self.track_ids)
        track = tracks.pop(from_index)
        tracks.insert(to_index, track)
        return Playlist(
            owner_id=self.owner_id,
            name=self.name,
            description=self.description,
            track_ids=tuple(tracks),
            is_favorite=self.is_favorite,
        )


class PlaylistBuilder:
    """Builder fluido para Playlist."""

    def __init__(self, owner_id: str) -> None:
        if not owner_id.strip():
            raise ValueError("owner_id es obligatorio")
        self._owner_id = owner_id.strip()
        self._name = ""
        self._description = ""
        self._track_ids: list[str] = []
        self._is_favorite = False

    def with_name(self, name: str) -> "PlaylistBuilder":
        cleaned = name.strip()
        if not cleaned:
            raise ValueError("El nombre de la playlist es obligatorio (RF-013)")
        if len(cleaned) > MAX_NAME_LEN:
            raise ValueError(f"El nombre supera {MAX_NAME_LEN} caracteres (RN-002)")
        self._name = cleaned
        return self

    def with_description(self, description: str) -> "PlaylistBuilder":
        self._description = description.strip()
        return self

    def add_track(self, video_id: str) -> "PlaylistBuilder":
        vid = video_id.strip()
        if not vid:
            raise ValueError("video_id vacío")
        if len(self._track_ids) >= MAX_TRACKS:
            raise ValueError(f"Máximo {MAX_TRACKS} pistas por playlist (RN-010)")
        self._track_ids.append(vid)
        return self

    def mark_favorite(self, favorite: bool = True) -> "PlaylistBuilder":
        self._is_favorite = favorite
        return self

    def build(self) -> Playlist:
        if not self._name:
            raise ValueError("Falta el nombre: llama with_name() antes de build()")
        return Playlist(
            owner_id=self._owner_id,
            name=self._name,
            description=self._description,
            track_ids=tuple(self._track_ids),
            is_favorite=self._is_favorite,
        )
