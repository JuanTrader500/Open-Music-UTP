"""Reglas de negocio de cuentas y sesión (RF-017, RF-018, RF-022)."""

from __future__ import annotations

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.auth.factory import creator_for
from app.auth.models import User
from app.auth.repository import AuthRepository
from app.auth.schemas import ExportResponse, LoginRequest, RegisterRequest, UserResponse
from app.core.config import Settings
from app.core.exceptions import (
    EmailTakenError,
    InvalidCredentialsError,
    ValidationFailedError,
)
from app.core.security import (
    LoginRateLimiter,
    create_access_token,
    hash_password,
    login_rate_limiter,
    verify_password,
)


class AuthService:
    """Única puerta de entrada del módulo auth para routers y otros módulos."""

    def __init__(
        self,
        db: Session,
        settings: Settings,
        *,
        repository: AuthRepository | None = None,
        limiter: LoginRateLimiter | None = None,
    ) -> None:
        """Recibe la sesión, la configuración y las dependencias inyectables."""
        self.db = db
        self.settings = settings
        self.repository = repository or AuthRepository(db)
        self.limiter = limiter or login_rate_limiter

    def register(self, data: RegisterRequest) -> User:
        """Crea una cuenta validando correo único y contraseña (RN-004)."""
        normalized_email = data.email.strip().lower()
        if self.repository.get_by_email(normalized_email) is not None:
            raise EmailTakenError()

        try:
            creator = creator_for(
                "registered",
                email=data.email,
                password=data.password,
                existing_emails=set(),
                min_password_length=self.settings.password_min_length,
            )
            candidate = creator.create_user()
        except ValueError as exc:
            raise ValidationFailedError(str(exc)) from exc

        try:
            user = self.repository.create(
                email=candidate.email,
                password_hash=hash_password(data.password),
            )
            self.db.commit()
        except IntegrityError as exc:
            self.db.rollback()
            raise EmailTakenError() from exc
        return user

    def login(self, data: LoginRequest, client_ip: str) -> tuple[str, int]:
        """Valida credenciales y devuelve el JWT y su vigencia en segundos."""
        normalized_email = data.email.strip().lower()
        rate_key = f"{normalized_email}|{client_ip}"
        self.limiter.check(rate_key, self.settings.login_attempts_per_minute)

        user = self.repository.get_by_email(normalized_email)
        if user is None or not verify_password(data.password, user.password_hash):
            self.limiter.register_failure(rate_key)
            raise InvalidCredentialsError()

        self.limiter.reset(rate_key)
        token = create_access_token(str(user.id), self.settings)
        return token, self.settings.access_token_expire_minutes * 60

    def export(self, user: User) -> ExportResponse:
        """Devuelve los datos personales del usuario (RF-022).

        Las colecciones de otros módulos se completan en fases posteriores.
        """
        return ExportResponse(user=UserResponse.model_validate(user))

    def delete_account(self, user: User) -> None:
        """Elimina la cuenta y sus datos por cascada (RF-022, RN-015)."""
        self.repository.delete(user)
        self.db.commit()
