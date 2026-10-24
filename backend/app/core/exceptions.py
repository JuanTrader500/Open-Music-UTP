"""Excepciones de dominio y manejadores de error de la API.

Toda respuesta de error tiene exactamente el cuerpo `{"code": ..., "message": ...}`
y mensajes en español sin detalles técnicos (RNF-008).
"""

from __future__ import annotations

import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = logging.getLogger(__name__)


class MusicAppError(Exception):
    """Base de todas las excepciones de la aplicación."""

    code = "INTERNAL_ERROR"
    http_status = 500
    default_message = "Ocurrió un error inesperado. Intenta de nuevo."

    def __init__(self, message: str | None = None) -> None:
        self.message = message or self.default_message
        super().__init__(self.message)


class ConfigurationError(MusicAppError):
    """Falta o es inválida una configuración del servidor."""

    code = "CONFIG_ERROR"
    http_status = 500
    default_message = "Error de configuración del servidor."


class InvalidQueryError(MusicAppError):
    """La consulta del usuario no cumple las reglas de búsqueda (RF-010)."""

    code = "INVALID_QUERY"
    http_status = 422
    default_message = "La consulta no es válida."


class ValidationFailedError(MusicAppError):
    """Los datos enviados por el cliente no son válidos."""

    code = "VALIDATION_ERROR"
    http_status = 422
    default_message = "Los datos enviados no son válidos."


class InvalidCredentialsError(MusicAppError):
    """Correo o contraseña incorrectos al iniciar sesión (RF-018)."""

    code = "INVALID_CREDENTIALS"
    http_status = 401
    default_message = "Correo o contraseña incorrectos."


class UnauthorizedError(MusicAppError):
    """La petición requiere una sesión válida (RF-018)."""

    code = "UNAUTHORIZED"
    http_status = 401
    default_message = "Debes iniciar sesión."


class EmailTakenError(MusicAppError):
    """El correo ya está registrado por otra cuenta (RN-004)."""

    code = "EMAIL_TAKEN"
    http_status = 409
    default_message = "Ese correo ya está registrado."


class RateLimitedError(MusicAppError):
    """Se superó el límite de intentos permitidos (RNF-029)."""

    code = "RATE_LIMITED"
    http_status = 429
    default_message = "Demasiados intentos. Espera un momento."

    def __init__(self, retry_after: int = 60, message: str | None = None) -> None:
        """Guarda los segundos que el cliente debe esperar antes de reintentar."""
        self.retry_after = retry_after
        super().__init__(message)


class NotFoundError(MusicAppError):
    """El recurso solicitado no existe."""

    code = "NOT_FOUND"
    http_status = 404
    default_message = "Recurso no encontrado."


class TrackNotFoundError(MusicAppError):
    """La canción solicitada no existe en el catálogo."""

    code = "TRACK_NOT_FOUND"
    http_status = 404
    default_message = "La canción no existe."


class DuplicateTrackError(MusicAppError):
    """La canción ya está en la playlist (RF-014)."""

    code = "DUPLICATE_TRACK"
    http_status = 409
    default_message = "La canción ya está en la playlist."


class PlaylistLimitError(MusicAppError):
    """El usuario alcanzó el máximo de playlists (RN-010)."""

    code = "PLAYLIST_LIMIT"
    http_status = 409
    default_message = "Alcanzaste el máximo de playlists."


class TrackLimitError(MusicAppError):
    """La playlist alcanzó el máximo de canciones (RN-010)."""

    code = "TRACK_LIMIT"
    http_status = 409
    default_message = "La playlist alcanzó el máximo de canciones."


class ProviderError(MusicAppError):
    """Fallo del proveedor de música; no debe tumbar la aplicación (RNF-023)."""

    code = "PROVIDER_ERROR"
    http_status = 502
    default_message = "No se pudo consultar el servicio de música."


class QuotaExceededError(ProviderError):
    """Cuota diaria agotada; la aplicación sigue con el catálogo guardado (RNF-024)."""

    code = "QUOTA_EXCEEDED"
    http_status = 503
    default_message = "La búsqueda nueva no está disponible por hoy."


class ServiceUnavailableError(MusicAppError):
    """Un servicio interno (por ejemplo la base de datos) no responde (RNF-025)."""

    code = "DB_UNAVAILABLE"
    http_status = 503
    default_message = "El servicio no está disponible. Intenta de nuevo en unos minutos."


# Mensajes fijos para los errores HTTP de Starlette que no son de dominio.
_HTTP_MESSAGES = {
    400: "La solicitud no es válida.",
    401: "Debes iniciar sesión.",
    403: "No tienes permiso para esta acción.",
    404: "Recurso no encontrado.",
    405: "Método no permitido.",
    409: "La solicitud entra en conflicto con el estado actual.",
    422: "Los datos enviados no son válidos.",
    429: "Demasiados intentos. Espera un momento.",
}

# Código de la API para cada estado HTTP de Starlette (mismo envelope que el dominio).
_HTTP_CODES = {
    400: "BAD_REQUEST",
    401: "UNAUTHORIZED",
    403: "FORBIDDEN",
    404: "NOT_FOUND",
    405: "METHOD_NOT_ALLOWED",
    409: "CONFLICT",
    422: "VALIDATION_ERROR",
    429: "RATE_LIMITED",
    500: "INTERNAL_ERROR",
    502: "BAD_GATEWAY",
    503: "SERVICE_UNAVAILABLE",
}


def _http_error_code(status_code: int) -> str:
    """Traduce un estado HTTP de Starlette a un código de error de la API."""
    return _HTTP_CODES.get(status_code, "HTTP_ERROR")


def register_exception_handlers(app: FastAPI) -> None:
    """Registra los manejadores que dan formato uniforme a las respuestas de error."""

    @app.exception_handler(MusicAppError)
    async def _handle_music_app_error(request: Request, exc: MusicAppError) -> JSONResponse:
        """Convierte una excepción de dominio en su respuesta JSON."""
        headers = (
            {"Retry-After": str(exc.retry_after)} if isinstance(exc, RateLimitedError) else None
        )
        return JSONResponse(
            status_code=exc.http_status,
            content={"code": exc.code, "message": exc.message},
            headers=headers,
        )

    @app.exception_handler(RequestValidationError)
    async def _handle_request_validation(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        """Devuelve un 422 genérico, sin detallar los campos inválidos."""
        return JSONResponse(
            status_code=422,
            content={"code": "VALIDATION_ERROR", "message": "Los datos enviados no son válidos."},
        )

    @app.exception_handler(StarletteHTTPException)
    async def _handle_http_exception(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        """Normaliza los errores HTTP de Starlette al formato de la API."""
        message = _HTTP_MESSAGES.get(exc.status_code, "No se pudo completar la solicitud.")
        return JSONResponse(
            status_code=exc.status_code,
            content={"code": _http_error_code(exc.status_code), "message": message},
        )

    @app.exception_handler(Exception)
    async def _handle_unexpected(request: Request, exc: Exception) -> JSONResponse:
        """Registra la traza y responde 500 sin exponer detalles internos."""
        logger.exception("Error no controlado en %s %s", request.method, request.url.path)
        return JSONResponse(
            status_code=500,
            content={
                "code": "INTERNAL_ERROR",
                "message": "Ocurrió un error inesperado. Intenta de nuevo.",
            },
        )
