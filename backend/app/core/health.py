"""Endpoints de salud del servicio (RNF-025)."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.exceptions import ServiceUnavailableError

router = APIRouter(tags=["salud"])


@router.get("/health")
def health() -> dict[str, str]:
    """Indica que el proceso está vivo, sin tocar la base de datos."""
    return {"status": "ok"}


@router.get("/health/ready")
def health_ready(db: Session = Depends(get_db)) -> dict[str, str]:
    """Comprueba que la base de datos responde; si no, informa indisponibilidad."""
    try:
        db.execute(text("SELECT 1"))
    except Exception as exc:
        raise ServiceUnavailableError() from exc
    return {"status": "ready"}
