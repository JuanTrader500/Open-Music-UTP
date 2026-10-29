"""Módulo listening: registro de escucha, historial y resumen. Archivo: router."""

from __future__ import annotations

from fastapi import APIRouter

# TODO (RF-023, RF-024 · RN-005, RN-006)
router = APIRouter(prefix="/listening", tags=["listening"])
