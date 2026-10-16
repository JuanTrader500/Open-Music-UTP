"""Prototype para RF-023/RF-024 (ESC-04).

Miles de registros de escucha con la misma forma (incluida simulación RF-028).
Clonar un prototipo es más barato que reconstruir y evita aliasing de estado.
RN-005: omitida si segundos < 30. RN-006: agregación por género/artista.
"""
from __future__ import annotations

from dataclasses import dataclass

SKIPPED_THRESHOLD_S = 30  # RN-005


@dataclass
class ListeningRecord:
    user_id: str
    video_id: str
    seconds_listened: int
    genre: str = "sin clasificar"
    artist: str = ""

    def __post_init__(self) -> None:
        if not self.user_id.strip():
            raise ValueError("user_id obligatorio (RF-023)")
        if not self.video_id.strip():
            raise ValueError("video_id obligatorio (RF-023)")
        if self.seconds_listened < 0:
            raise ValueError("seconds_listened no puede ser negativo")

    @property
    def skipped(self) -> bool:
        """RN-005: pista omitida si se escuchó menos de 30 s."""
        return self.seconds_listened < SKIPPED_THRESHOLD_S

    def clone(self, **overrides) -> "ListeningRecord":
        """Prototype: copia profunda con cambios puntuales.

        Ejemplo: prototipo.clone(user_id="u2", video_id="sim_rock_02")
        """
        data = {
            "user_id": self.user_id,
            "video_id": self.video_id,
            "seconds_listened": self.seconds_listened,
            "genre": self.genre,
            "artist": self.artist,
        }
        data.update(overrides)
        return ListeningRecord(
            user_id=data["user_id"],
            video_id=data["video_id"],
            seconds_listened=data["seconds_listened"],
            genre=data["genre"],
            artist=data["artist"],
        )
