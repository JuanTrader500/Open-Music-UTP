"""Excepciones de dominio compartidas por todos los módulos."""


class MusicAppError(Exception):
    """Base de todas las excepciones de la aplicación."""


class ConfigurationError(MusicAppError):
    """Falta o es inválida una configuración (por ejemplo, la clave de YouTube)."""


class InvalidQueryError(MusicAppError):
    """Consulta inválida, p. ej. menos de 2 caracteres (RF-010)."""


class ProviderError(MusicAppError):
    """Fallo del proveedor de música; no debe tumbar la app (RNF-023)."""


class QuotaExceededError(ProviderError):
    """Cuota diaria agotada; la app sigue con el catálogo guardado (RNF-024)."""
