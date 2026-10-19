"""Módulo recommendations: onboarding y recomendaciones con reglas estáticas. Archivo: router."""

from __future__ import annotations

from fastapi import APIRouter

# TODO (RF-021, RF-025 a RF-027 · RN-006 a RN-009)
router = APIRouter(prefix="/recommendations", tags=["recommendations"])
