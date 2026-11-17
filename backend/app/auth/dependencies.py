"""Dependencias de autenticación para rutas protegidas (RF-018)."""

from __future__ import annotations

import uuid

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from app.auth.models import User
from app.auth.repository import AuthRepository
from app.core.config import Settings, get_settings
from app.core.database import get_db
from app.core.exceptions import UnauthorizedError
from app.core.security import bearer_scheme, decode_access_token


def _resolve_user(
    credentials: HTTPAuthorizationCredentials | None,
    db: Session,
    settings: Settings,
) -> User:
    """Valida el Bearer y carga el usuario; lanza 401 si no es válido."""
    if credentials is None:
        raise UnauthorizedError()
    subject = decode_access_token(credentials.credentials, settings)
    try:
        user_id = uuid.UUID(subject)
    except ValueError as exc:
        raise UnauthorizedError() from exc
    user = AuthRepository(db).get_by_id(user_id)
    if user is None:
        raise UnauthorizedError()
    return user


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> User:
    """Devuelve el usuario autenticado o responde 401."""
    return _resolve_user(credentials, db, settings)


def get_optional_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> User | None:
    """Devuelve el usuario si hay token válido; `None` si no hay token."""
    if credentials is None:
        return None
    return _resolve_user(credentials, db, settings)
