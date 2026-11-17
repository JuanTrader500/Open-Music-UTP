"""Contratos Pydantic del módulo auth (RF-017, RF-018, RF-022)."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


class RegisterRequest(BaseModel):
    """Datos de registro de una cuenta (RF-017, RNF-032)."""

    email: str = Field(min_length=3, max_length=254)
    password: str = Field(min_length=1, max_length=128)
    accept_privacy: bool

    @field_validator("accept_privacy")
    @classmethod
    def _privacy_must_be_accepted(cls, value: bool) -> bool:
        """Exige el consentimiento explícito de privacidad (RNF-032)."""
        if value is not True:
            raise ValueError("Debes aceptar la política de privacidad.")
        return value


class LoginRequest(BaseModel):
    """Credenciales de inicio de sesión (RF-018)."""

    email: str = Field(min_length=3, max_length=254)
    password: str = Field(min_length=1, max_length=128)


class RegisterResponse(BaseModel):
    """Cuenta creada; nunca incluye el hash de la contraseña."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: str
    created_at: datetime


class TokenResponse(BaseModel):
    """Token de acceso emitido por el login."""

    access_token: str
    token_type: str = "bearer"
    expires_in: int


class UserResponse(BaseModel):
    """Datos públicos del usuario autenticado."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: str
    is_simulated: bool
    created_at: datetime


class ExportResponse(BaseModel):
    """Exportación de datos del usuario (RF-022).

    En esta fase las colecciones de otros módulos se devuelven vacías; se
    completan cuando existan sus servicios (Fase 3 y 4).
    """

    user: UserResponse
    playlists: list[Any] = Field(default_factory=list)
    favorites: list[Any] = Field(default_factory=list)
    listening_events: list[Any] = Field(default_factory=list)
    preferences: dict[str, list[Any]] = Field(default_factory=lambda: {"genres": [], "artists": []})
