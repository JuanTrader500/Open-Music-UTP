"""Endpoints REST de búsqueda y catálogo"""

from __future__ import annotations

from fastapi import APIRouter

# TODO (RF-010, RF-011)
router = APIRouter(prefix="/catalog", tags=["catalog"])
