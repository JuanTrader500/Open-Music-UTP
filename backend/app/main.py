"""Punto de entrada de FastAPI: crea la aplicación, los middlewares y los routers.

Al arrancar se configura el registro de eventos y se valida la configuración
obligatoria; si falta una variable, el proceso falla indicando su nombre.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.auth.router import router as auth_router
from app.catalog.router import router as catalog_router
from app.core.config import get_settings
from app.core.exceptions import register_exception_handlers
from app.core.health import router as health_router
from app.core.logging import (
    RequestIdMiddleware,
    SecurityHeadersMiddleware,
    configure_logging,
)
from app.listening.router import router as listening_router
from app.playlists.router import router as playlists_router
from app.recommendations.router import router as recommendations_router


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Configura los registros y valida la configuración al arrancar."""
    settings = get_settings()
    configure_logging(settings.log_level)
    settings.validate_runtime()
    yield


def create_app() -> FastAPI:
    """Construye la aplicación con CORS, middlewares, manejadores y routers."""
    settings = get_settings()
    app = FastAPI(
        title="Open Music UTP API",
        version="2.1.0",
        docs_url="/api/docs",
        openapi_url="/api/openapi.json",
        redoc_url=None,
        lifespan=lifespan,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=False,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
        allow_headers=["Authorization", "Content-Type"],
    )
    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(RequestIdMiddleware)
    register_exception_handlers(app)
    app.include_router(health_router, prefix="/api")
    for module_router in (
        auth_router,
        catalog_router,
        playlists_router,
        listening_router,
        recommendations_router,
    ):
        app.include_router(module_router, prefix="/api")
    return app


app = create_app()
