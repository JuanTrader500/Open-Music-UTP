"""Pruebas del Decorator de transacciones (entrega 2, RNF-021).

La sesión se sustituye por un contador para comprobar commit/rollback sin base
de datos. También se verifica que auth traduzca `IntegrityError` sin hacer un
segundo rollback y que los repositorios no confirmen transacciones.
"""

from __future__ import annotations

import ast
from pathlib import Path
from types import SimpleNamespace

import pytest
from sqlalchemy.exc import IntegrityError

from app.auth.schemas import RegisterRequest
from app.auth.service import AuthService
from app.catalog.service import CatalogService
from app.core.config import Settings
from app.core.exceptions import EmailTakenError, TrackNotFoundError
from app.core.transactions import transactional

APP = Path(__file__).resolve().parents[2] / "app"


class _FakeDb:
    """Sesión falsa que cuenta confirmaciones y reversiones."""

    def __init__(self) -> None:
        self.commits = 0
        self.rollbacks = 0

    def commit(self) -> None:
        self.commits += 1

    def rollback(self) -> None:
        self.rollbacks += 1


class _Service:
    """Servicio mínimo para probar el decorador de forma aislada."""

    def __init__(self, db: _FakeDb) -> None:
        self.db = db

    @transactional
    def write(self, value: str) -> str:
        return value

    @transactional
    def fail(self) -> None:
        raise RuntimeError("fallo del método")


class _AuthRepository:
    """Repositorio de auth falso, con error de integridad opcional."""

    def __init__(self, *, create_error: Exception | None = None) -> None:
        self._create_error = create_error
        self.deleted: list[object] = []

    def get_by_email(self, email: str) -> None:
        return None

    def create(self, **values) -> SimpleNamespace:
        if self._create_error is not None:
            raise self._create_error
        return SimpleNamespace(id=1, email=values["email"])

    def delete(self, user: object) -> None:
        self.deleted.append(user)


class _FailingDeleteRepository(_AuthRepository):
    def delete(self, user: object) -> None:
        raise RuntimeError("fallo al eliminar")


class _CatalogRepository:
    """Repositorio de catálogo falso para `mark_unplayable`."""

    def __init__(self, *, found: bool = True) -> None:
        self.found = found

    def mark_unplayable(self, track_id: str) -> bool:
        return self.found


def _settings() -> Settings:
    return Settings(search_min_chars=2)


def _register_request() -> RegisterRequest:
    return RegisterRequest(
        email="ana@example.com",
        password="Clave-segura-123",
        accept_privacy=True,
    )


def _transaction_calls(path: Path) -> list[str]:
    """Devuelve las llamadas a `.commit()`/`.rollback()` de un archivo."""
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    calls: list[str] = []
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr in {"commit", "rollback"}
        ):
            calls.append(f"{path.relative_to(APP)}:{node.lineno}")
    return calls


# ----------------------------------- Decorador --------------------------------------------
def test_successful_method_commits_exactly_once():
    db = _FakeDb()

    assert _Service(db).write("ok") == "ok"

    assert (db.commits, db.rollbacks) == (1, 0)


def test_method_with_exception_rolls_back_once_and_propagates():
    db = _FakeDb()

    with pytest.raises(RuntimeError, match="fallo del método"):
        _Service(db).fail()

    assert (db.commits, db.rollbacks) == (0, 1)


def test_decorator_requires_a_session_in_self_db():
    class _NoDb:
        @transactional
        def run(self) -> None:
            pass

    with pytest.raises(AttributeError, match="self.db"):
        _NoDb().run()


# -------------------------------------- Auth ----------------------------------------------
def test_register_commits_exactly_once():
    db = _FakeDb()
    service = AuthService(db, _settings(), repository=_AuthRepository())

    user = service.register(_register_request())

    assert user.email == "ana@example.com"
    assert (db.commits, db.rollbacks) == (1, 0)


def test_register_duplicate_email_rolls_back_once_and_returns_email_taken():
    db = _FakeDb()
    duplicate = IntegrityError("INSERT INTO users", {}, Exception("duplicate key"))
    service = AuthService(db, _settings(), repository=_AuthRepository(create_error=duplicate))

    with pytest.raises(EmailTakenError):
        service.register(_register_request())

    # Si quedara el rollback local de auth habría dos reversiones.
    assert (db.commits, db.rollbacks) == (0, 1)


def test_delete_account_commits_exactly_once():
    db = _FakeDb()
    repository = _AuthRepository()
    user = SimpleNamespace(id=1)

    AuthService(db, _settings(), repository=repository).delete_account(user)

    assert repository.deleted == [user]
    assert (db.commits, db.rollbacks) == (1, 0)


def test_delete_account_failure_rolls_back_once():
    db = _FakeDb()
    service = AuthService(db, _settings(), repository=_FailingDeleteRepository())

    with pytest.raises(RuntimeError, match="fallo al eliminar"):
        service.delete_account(SimpleNamespace(id=1))

    assert (db.commits, db.rollbacks) == (0, 1)


# ------------------------------------- Catálogo -------------------------------------------
def _catalog_service(db: _FakeDb, repository: _CatalogRepository) -> CatalogService:
    return CatalogService(db, _settings(), provider=SimpleNamespace(), repository=repository)


def test_catalog_mark_unplayable_commits_exactly_once():
    db = _FakeDb()

    _catalog_service(db, _CatalogRepository(found=True)).mark_unplayable("t1")

    assert (db.commits, db.rollbacks) == (1, 0)


def test_catalog_mark_unplayable_not_found_rolls_back_once():
    db = _FakeDb()

    with pytest.raises(TrackNotFoundError):
        _catalog_service(db, _CatalogRepository(found=False)).mark_unplayable("t1")

    assert (db.commits, db.rollbacks) == (0, 1)


# ------------------------- Repositorios y servicios sin commit local ----------------------
def test_repositories_do_not_commit_or_rollback():
    offenders: list[str] = []
    for path in sorted(APP.rglob("repository.py")):
        offenders.extend(_transaction_calls(path))

    assert offenders == []


def test_services_delegate_commit_and_rollback_to_the_decorator():
    offenders = _transaction_calls(APP / "catalog/service.py")
    offenders += _transaction_calls(APP / "auth/service.py")

    assert offenders == []
