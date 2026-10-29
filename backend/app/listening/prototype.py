"""Prototype para registros de escucha (RF-023, RF-024).

Muchos registros comparten la misma forma (incluida la simulación). Clonar un
prototipo es más barato que reconstruir y evita compartir estado mutable.
El umbral de omisión se recibe como parámetro (RN-005).
"""

from __future__ import annotations

from dataclasses import dataclass, replace


@dataclass
class ListeningRecord:
    """Evento de escucha de una pista por un usuario.

    Es mutable a propósito: el patrón Prototype lo clona y luego ajusta campos
    (por ejemplo `seconds_listened`) para simular escuchas sin recrear el objeto.
    """

    user_id: str
    track_id: str
    seconds_listened: int
    genre: str = "sin clasificar"
    artist: str = ""

    def __post_init__(self) -> None:
        """Valida los campos obligatorios y los valores no negativos."""
        if not self.user_id.strip():
            raise ValueError("El usuario es obligatorio (RF-023).")
        if not self.track_id.strip():
            raise ValueError("La pista es obligatoria (RF-023).")
        if self.seconds_listened < 0:
            raise ValueError("Los segundos escuchados no pueden ser negativos.")

    def is_skipped(self, threshold_s: int) -> bool:
        """RN-005: la pista se considera omitida si se escuchó menos del umbral."""
        return self.seconds_listened < threshold_s

    def clone(self, **overrides) -> ListeningRecord:
        """Devuelve una copia independiente con los cambios indicados."""
        return replace(self, **overrides)
