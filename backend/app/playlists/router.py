"""Módulo playlists: playlists, favoritos e importación de datos de invitado. Archivo: router."""

from __future__ import annotations

from fastapi import APIRouter

# TODO (RF-013 a RF-016, RF-019, RF-020 · RN-010)
router = APIRouter(prefix="/playlists", tags=["playlists"])
