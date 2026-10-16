"""Factory Method para RF-017/RF-018 (ESC-03).

El cliente pide "crear un usuario" sin acoplarse a las clases concretas.
Cada subclase de UserCreator decide QUÉ tipo instanciar y con QUÉ validación.
RN-004: correo único (se deja el chequeo de unicidad al repositorio, aquí formato).
RN-015: la clave nunca queda en claro (bandera password_hashed).
"""
from __future__ import annotations

from abc import ABC, abstractmethod

from pydantic import BaseModel, ConfigDict


class User(BaseModel):
    """Modelo base, igual estilo que TrackMetadata y Settings (pydantic)."""

    model_config = ConfigDict(frozen=True)

    kind: str
    email: str | None = None
    password_hashed: bool = False
    can_persist: bool = False


class GuestUser(User):
    kind: str = "guest"
    email: str | None = None
    password_hashed: bool = False
    can_persist: bool = False


class RegisteredUser(User):
    kind: str = "registered"
    email: str
    password_hashed: bool = True
    can_persist: bool = True


class AdminUser(User):
    kind: str = "admin"
    email: str
    password_hashed: bool = True
    can_persist: bool = True


def _normalize_email(email: str) -> str:
    cleaned = email.strip().lower()
    if "@" not in cleaned or "." not in cleaned.split("@")[-1]:
        raise ValueError(f"Correo inválido: {email!r} (RN-004)")
    return cleaned


class UserCreator(ABC):
    """Creador abstracto: declara el Factory Method."""

    @abstractmethod
    def create_user(self) -> User:
        """Factory Method: crea un usuario sin exponer la clase concreta."""


class GuestCreator(UserCreator):
    def create_user(self) -> GuestUser:
        return GuestUser()


class RegisteredCreator(UserCreator):
    def __init__(self, email: str, password: str, existing_emails: set[str] | None = None) -> None:
        self._email = email
        self._password = password
        self._existing = {e.lower() for e in (existing_emails or set())}

    def create_user(self) -> RegisteredUser:
        email = _normalize_email(self._email)
        if len(self._password) < 8:
            raise ValueError("La clave debe tener al menos 8 caracteres (RNF-026)")
        if email in self._existing:
            raise ValueError(f"Correo ya registrado: {email} (RN-004)")
        # En producción aquí se hashea con Argon2/bcrypt (RNF-026); no se guarda en claro.
        return RegisteredUser(email=email)


class AdminCreator(UserCreator):
    def __init__(self, email: str, password: str) -> None:
        self._email = email
        self._password = password

    def create_user(self) -> AdminUser:
        email = _normalize_email(self._email)
        if len(self._password) < 8:
            raise ValueError("La clave debe tener al menos 8 caracteres (RNF-026)")
        return AdminUser(email=email)


def creator_for(kind: str, **kwargs) -> UserCreator:
    """Selector simple para no repartir if/elif por el código cliente."""
    kinds = {"guest": GuestCreator, "registered": RegisteredCreator, "admin": AdminCreator}
    try:
        cls = kinds[kind]
    except KeyError:
        raise ValueError(f"Tipo de usuario desconocido: {kind!r}") from None
    return cls(**kwargs)  # type: ignore[call-arg]
