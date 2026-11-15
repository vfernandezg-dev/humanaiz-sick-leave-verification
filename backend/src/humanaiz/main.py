"""Fábrica de la aplicación. Arranque: `uvicorn --factory humanaiz.main:create_app`."""

from __future__ import annotations

import logging
import re
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import APIRouter, FastAPI, Request

from humanaiz import __version__
from humanaiz.api import health
from humanaiz.config import Settings, enforce_boot_guard, get_settings
from humanaiz.db import Database
from humanaiz.errors import install_error_handlers
from humanaiz.logging import configure_logging
from humanaiz.middleware import BodyLimit, RequestContextMiddleware

logger = logging.getLogger(__name__)

API_PREFIX = "/api/v1"
_UPLOAD_PATH = re.compile(rf"^{API_PREFIX}/descansos/?$")
_DEFAULT_BODY_LIMIT = 64 * 1024
_MULTIPART_OVERHEAD = 64 * 1024


def make_body_limit(settings: Settings) -> BodyLimit:
    upload_limit = settings.max_upload_bytes + _MULTIPART_OVERHEAD

    def limit(method: str, path: str) -> int:
        if method == "POST" and _UPLOAD_PATH.match(path):
            return upload_limit
        return _DEFAULT_BODY_LIMIT

    return limit


def get_app_settings(request: Request) -> Settings:
    return request.app.state.settings


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    configure_logging(settings.log_level)
    presentes = enforce_boot_guard(settings)
    if presentes:
        logger.warning(
            "variables de entorno ignoradas por seguridad (no permitidas en producción): %s",
            ", ".join(presentes),
        )

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        app.state.db = Database(settings.database_url, pool_size=settings.db_pool_size)
        try:
            yield
        finally:
            await app.state.db.dispose()

    app = FastAPI(
        title="HumanAIz API",
        version=__version__,
        lifespan=lifespan,
        docs_url="/api/docs" if settings.enable_docs else None,
        redoc_url=None,
        openapi_url="/api/openapi.json" if settings.enable_docs else None,
    )
    app.state.settings = settings
    app.add_middleware(RequestContextMiddleware, body_limit=make_body_limit(settings))
    install_error_handlers(app)

    api = APIRouter(prefix=API_PREFIX)
    api.include_router(health.router)
    app.include_router(api)
    return app
