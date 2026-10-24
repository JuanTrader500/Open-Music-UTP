"""Módulo auth: registro, sesión y privacidad de datos. Archivo: router."""

from __future__ import annotations

from fastapi import APIRouter

# TODO (RF-017, RF-018, RF-020, RF-022 · RNF-026 a RNF-029 · RN-004, RN-015)
router = APIRouter(prefix="/auth", tags=["auth"])
