"""Hash de contraseñas, tokens JWT y rate limit (RNF-026, RNF-027, RNF-029).

El hash usa Argon2id y el token es un JWT firmado con HS256. El rate limit de
login vive en memoria del proceso; se documenta como límite de desarrollo
(D-06 del plan).
"""

from __future__ import annotations

import time
from collections import defaultdict, deque
from datetime import UTC, datetime, timedelta
from threading import Lock
from typing import Any

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError
from fastapi.security import HTTPBearer

from app.core.config import Settings
from app.core.exceptions import RateLimitedError, UnauthorizedError

_hasher = PasswordHasher()

#: Esquema Bearer sin auto-error para responder con el envelope propio de la API.
bearer_scheme = HTTPBearer(auto_error=False)

_JWT_ALGORITHM = "HS256"
_RATE_LIMIT_WINDOW_S = 60


def hash_password(password: str) -> str:
    """Devuelve el hash Argon2id de una contraseña en claro."""
    return _hasher.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    """Comprueba una contraseña contra su hash sin propagar errores técnicos."""
    try:
        return _hasher.verify(password_hash, password)
    except (VerifyMismatchError, VerificationError, InvalidHashError):
        return False


def create_access_token(
    user_id: str,
    settings: Settings,
    *,
    now: datetime | None = None,
) -> str:
    """Crea un JWT con `sub`, `iat` y `exp` (RF-018, RNF-027)."""
    issued_at = now or datetime.now(UTC)
    expires_at = issued_at + timedelta(minutes=settings.access_token_expire_minutes)
    payload: dict[str, Any] = {
        "sub": str(user_id),
        "iat": int(issued_at.timestamp()),
        "exp": int(expires_at.timestamp()),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=_JWT_ALGORITHM)


def decode_access_token(token: str, settings: Settings) -> str:
    """Valida el JWT y devuelve el id de usuario; lanza `UnauthorizedError`."""
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[_JWT_ALGORITHM])
    except jwt.PyJWTError as exc:
        raise UnauthorizedError() from exc
    subject = payload.get("sub")
    if not isinstance(subject, str) or not subject:
        raise UnauthorizedError()
    return subject


class LoginRateLimiter:
    """Límite de intentos de login por clave (correo + IP) en memoria."""

    def __init__(self) -> None:
        self._attempts: dict[str, deque[float]] = defaultdict(deque)
        self._lock = Lock()

    def check(self, key: str, limit: int) -> None:
        """Lanza `RateLimitedError` si la clave ya agotó sus intentos."""
        now = time.monotonic()
        with self._lock:
            attempts = self._attempts[key]
            self._discard_expired(attempts, now)
            if len(attempts) >= limit:
                retry_after = max(1, int(_RATE_LIMIT_WINDOW_S - (now - attempts[0])))
                raise RateLimitedError(retry_after=retry_after)

    def register_failure(self, key: str) -> None:
        """Registra un intento fallido."""
        with self._lock:
            self._attempts[key].append(time.monotonic())

    def reset(self, key: str) -> None:
        """Limpia los intentos de una clave tras un login exitoso."""
        with self._lock:
            self._attempts.pop(key, None)

    def clear(self) -> None:
        """Vacía todo el estado (usado por las pruebas)."""
        with self._lock:
            self._attempts.clear()

    @staticmethod
    def _discard_expired(attempts: deque[float], now: float) -> None:
        """Elimina intentos fuera de la ventana de tiempo."""
        while attempts and now - attempts[0] >= _RATE_LIMIT_WINDOW_S:
            attempts.popleft()


#: Instancia única usada por el servicio de auth.
login_rate_limiter = LoginRateLimiter()
