"""Factory Method para crear usuarios (RF-017, RF-018).

El cliente pide "crear un usuario" sin acoplarse a las clases concretas; cada
subclase de `UserCreator` decide qué tipo instanciar y con qué validación.
RN-004: correo único (normalizado a minúsculas) y contraseña de al menos `n`
caracteres. RNF-026: la contraseña nunca se guarda en claro.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from pydantic import BaseModel, ConfigDict


class User(BaseModel):
    """Modelo base de usuario, con el mismo estilo pydantic que el resto del sistema."""

    model_config = ConfigDict(frozen=True)

    kind: str
    email: str | None = None
    password_hashed: bool = False
    can_persist: bool = False


class GuestUser(User):
    """Usuario invitado: sin correo, sin contraseña y sin persistencia (RF-019)."""

    kind: str = "guest"
    email: str | None = None
    password_hashed: bool = False
    can_persist: bool = False


class RegisteredUser(User):
    """Usuario registrado: con correo y contraseña hasheada (RF-017)."""

    kind: str = "registered"
    email: str
    password_hashed: bool = True
    can_persist: bool = True


def _normalize_email(email: str) -> str:
    """RN-004: normaliza el correo a minúsculas y comprueba su formato básico."""
    cleaned = email.strip().lower()
    if "@" not in cleaned or "." not in cleaned.split("@")[-1]:
        raise ValueError(f"El correo no es válido: {email!r} (RN-004).")
    return cleaned


class UserCreator(ABC):
    """Creador abstracto que declara el Factory Method."""

    @abstractmethod
    def create_user(self) -> User:
        """Crea un usuario sin exponer la clase concreta."""


class GuestCreator(UserCreator):
    """Crea un usuario invitado sin correo ni contraseña."""

    def create_user(self) -> GuestUser:
        """Devuelve un `GuestUser` con permisos limitados."""
        return GuestUser()


class RegisteredCreator(UserCreator):
    """Crea un usuario registrado validando correo y contraseña."""

    def __init__(
        self,
        email: str,
        password: str,
        existing_emails: set[str] | None = None,
        *,
        min_password_length: int,
    ) -> None:
        """Guarda los datos de registro y la longitud mínima de la contraseña."""
        self._email = email
        self._password = password
        self._existing = {value.lower() for value in (existing_emails or set())}
        self._min_password_length = min_password_length

    def create_user(self) -> RegisteredUser:
        """Valida formato, longitud de contraseña y unicidad del correo."""
        email = _normalize_email(self._email)
        if len(self._password) < self._min_password_length:
            raise ValueError(
                f"La clave debe tener al menos {self._min_password_length} caracteres (RN-004)."
            )
        if email in self._existing:
            raise ValueError(f"El correo ya está registrado: {email} (RN-004).")
        return RegisteredUser(email=email)


def creator_for(kind: str, **kwargs) -> UserCreator:
    """Devuelve el creador correspondiente al tipo de usuario indicado."""
    kinds = {"guest": GuestCreator, "registered": RegisteredCreator}
    try:
        creator_class = kinds[kind]
    except KeyError:
        raise ValueError(f"Tipo de usuario desconocido: {kind!r}") from None
    return creator_class(**kwargs)  # type: ignore[call-arg]
