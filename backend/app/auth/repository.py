"""Acceso a datos de usuarios (RF-017, RF-018)."""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.models import User


class AuthRepository:
    """Consultas y escrituras de la tabla `users`."""

    def __init__(self, db: Session) -> None:
        """Guarda la sesión de base de datos de la petición."""
        self.db = db

    def get_by_email(self, email: str) -> User | None:
        """Busca un usuario por correo ya normalizado."""
        return self.db.scalar(select(User).where(User.email == email))

    def get_by_id(self, user_id: uuid.UUID) -> User | None:
        """Busca un usuario por su identificador."""
        return self.db.get(User, user_id)

    def create(
        self,
        *,
        email: str,
        password_hash: str,
        is_simulated: bool = False,
    ) -> User:
        """Inserta un usuario y devuelve la instancia con sus valores por defecto."""
        user = User(
            email=email,
            password_hash=password_hash,
            is_simulated=is_simulated,
        )
        self.db.add(user)
        self.db.flush()
        self.db.refresh(user)
        return user

    def delete(self, user: User) -> None:
        """Elimina un usuario; las FKs en cascada limpian sus datos."""
        self.db.delete(user)
        self.db.flush()
