"""Registros estructurados en JSON y middlewares transversales (RNF-034, RNF-030)."""

from __future__ import annotations

import json
import logging
import re
import sys
import time
import uuid
from contextvars import ContextVar
from datetime import UTC, datetime
from typing import Any

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

#: Identificador de la petición en curso; "-" cuando no hay una petición activa.
request_id_var: ContextVar[str] = ContextVar("request_id", default="-")

_REQUEST_ID_PATTERN = re.compile(r"^[A-Za-z0-9-]{8,64}$")
_RESERVED_LOG_ATTRS = frozenset(logging.makeLogRecord({}).__dict__) | {"message", "asctime"}


class JsonFormatter(logging.Formatter):
    """Serializa cada registro como una línea JSON con los campos del SRS."""

    def format(self, record: logging.LogRecord) -> str:
        """Construye el objeto JSON del registro, incluidos los campos extra."""
        payload: dict[str, Any] = {
            "timestamp": datetime.now(UTC).isoformat(timespec="milliseconds"),
            "level": record.levelname,
            "module": record.name,
            "message": record.getMessage(),
            "request_id": request_id_var.get(),
        }
        for key, value in record.__dict__.items():
            if key not in _RESERVED_LOG_ATTRS and key not in payload:
                payload[key] = value
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False, default=str)


def configure_logging(level: str) -> None:
    """Configura un único manejador de salida estándar con formato JSON."""
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())
    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(level.upper())


logger = logging.getLogger("app.request")


class RequestIdMiddleware(BaseHTTPMiddleware):
    """Asigna un identificador por petición y registra una línea de acceso."""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        """Reutiliza o genera el identificador, lo devuelve y registra el acceso."""
        incoming = request.headers.get("X-Request-ID", "")
        request_id = incoming if _REQUEST_ID_PATTERN.fullmatch(incoming) else uuid.uuid4().hex
        token = request_id_var.set(request_id)
        start = time.perf_counter()
        try:
            response = await call_next(request)
            duration_ms = round((time.perf_counter() - start) * 1000, 2)
            response.headers["X-Request-ID"] = request_id
            logger.info(
                "Petición completada",
                extra={
                    "method": request.method,
                    "path": request.url.path,
                    "status": response.status_code,
                    "duration_ms": duration_ms,
                },
            )
            return response
        finally:
            request_id_var.reset(token)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Añade cabeceras de seguridad y evita el caché en la API (RNF-030)."""

    #: Rutas de documentación que sí pueden almacenarse en caché.
    _NO_STORE_EXCEPTIONS = ("/api/docs", "/api/openapi.json")

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        """Agrega las cabeceras de seguridad a la respuesta."""
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "no-referrer"
        path = request.url.path
        if path.startswith("/api/") and path not in self._NO_STORE_EXCEPTIONS:
            response.headers["Cache-Control"] = "no-store"
        return response
