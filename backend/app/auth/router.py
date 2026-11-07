"""Endpoints de registro, sesión y privacidad (RF-017, RF-018, RF-022)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request, Response, status
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.auth.models import User
from app.auth.schemas import (
    ExportResponse,
    LoginRequest,
    RegisterRequest,
    RegisterResponse,
    TokenResponse,
    UserResponse,
)
from app.auth.service import AuthService
from app.core.config import Settings, get_settings
from app.core.database import get_db

router = APIRouter(prefix="/auth", tags=["auth"])


def _service(db: Session, settings: Settings) -> AuthService:
    """Construye el servicio con las dependencias de la petición."""
    return AuthService(db, settings)


@router.post(
    "/register",
    response_model=RegisterResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Registrar una cuenta",
)
def register(
    payload: RegisterRequest,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> User:
    """Crea una cuenta y devuelve sus datos públicos (RF-017)."""
    return _service(db, settings).register(payload)


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Iniciar sesión",
)
def login(
    payload: LoginRequest,
    request: Request,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> TokenResponse:
    """Valida credenciales y emite un JWT (RF-018, RNF-027)."""
    client_ip = request.client.host if request.client else "unknown"
    token, expires_in = _service(db, settings).login(payload, client_ip)
    return TokenResponse(access_token=token, expires_in=expires_in)


@router.post(
    "/logout",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
    summary="Cerrar sesión",
)
def logout(_user: User = Depends(get_current_user)) -> Response:
    """Cierra la sesión; el cliente descarta el token (JWT sin estado)."""
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get(
    "/me",
    response_model=UserResponse,
    summary="Datos del usuario autenticado",
)
def me(user: User = Depends(get_current_user)) -> User:
    """Devuelve los datos públicos del usuario autenticado (RF-018)."""
    return user


@router.get(
    "/export",
    response_model=ExportResponse,
    summary="Exportar datos personales",
)
def export(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> ExportResponse:
    """Exporta los datos personales del usuario (RF-022)."""
    return _service(db, settings).export(user)


@router.delete(
    "/account",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
    summary="Eliminar la cuenta",
)
def delete_account(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> Response:
    """Elimina la cuenta y sus datos en cascada (RF-022, RN-015)."""
    _service(db, settings).delete_account(user)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
