"""Fábrica de la aplicación. Arranque: `uvicorn --factory humanaiz.main:create_app`."""

from __future__ import annotations

import asyncio
import contextlib
import logging
import re
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import APIRouter, Depends, FastAPI

from humanaiz import __version__
from humanaiz.api import (
    analisis,
    auth,
    colaboradores,
    descansos,
    health,
    llm,
    public_config,
)
from humanaiz.api import (
    demo as demo_api,
)
from humanaiz.config import ConfigError, Settings, enforce_boot_guard, get_settings
from humanaiz.db import Database
from humanaiz.errors import install_error_handlers
from humanaiz.logging import configure_logging
from humanaiz.middleware import BodyLimit, RequestContextMiddleware
from humanaiz.security.ratelimit import RateLimiter, general_rate_limit
from humanaiz.services import demo
from humanaiz.storage.factory import crear_storage
from humanaiz.tasks import purge_loop
from humanaiz.web import WebEstatica

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
        db = Database(settings.database_url, pool_size=settings.db_pool_size)
        storage = crear_storage(settings, db)
        app.state.db = db
        app.state.storage = storage
        # Acota cuántos documentos se decodifican a la vez (memoria y CPU).
        app.state.normalize_slots = asyncio.Semaphore(settings.normalize_max_concurrency)
        # Tope global de llamadas simultáneas a proveedores de IA.
        app.state.analysis_slots = asyncio.Semaphore(settings.analysis_max_concurrency)
        app.state.analisis_en_vuelo = set()
        purga: asyncio.Task[None] | None = None
        try:
            # Impide arrancar con cuentas de prueba públicas junto a datos reales.
            async with db.session() as session:
                await demo.assert_mode_consistency(session, settings)
            if settings.purge_interval_seconds > 0:
                purga = asyncio.create_task(purge_loop(db, storage, settings), name="purga")
            yield
        finally:
            if purga is not None:
                purga.cancel()
                with contextlib.suppress(asyncio.CancelledError):
                    await purga
            # Los análisis en curso ya están pagados por sus usuarios: se les
            # da tiempo a terminar y guardar antes de cerrar la base de datos.
            pendientes = set(app.state.analisis_en_vuelo)
            if pendientes:
                await asyncio.wait(pendientes, timeout=settings.analysis_deadline_seconds + 10)
            await db.dispose()

    app = FastAPI(
        title="HumanAIz API",
        version=__version__,
        lifespan=lifespan,
        docs_url="/api/docs" if settings.enable_docs else None,
        redoc_url=None,
        openapi_url="/api/openapi.json" if settings.enable_docs else None,
    )
    app.state.settings = settings
    app.state.limiter = RateLimiter(settings.rate_limit_storage_uri)
    app.add_middleware(RequestContextMiddleware, body_limit=make_body_limit(settings))
    if settings.static_dir is not None:
        if not (settings.static_dir / "index.html").is_file():
            raise ConfigError(f"STATIC_DIR no contiene index.html: {settings.static_dir}")
        # Un solo contenedor (Vercel): la API sirve también la web, con las
        # cabeceras de seguridad que en docker compose pone Caddy.
        app.add_middleware(WebEstatica, directorio=settings.static_dir)
    install_error_handlers(app)

    # Las sondas quedan fuera del límite general: las usa el orquestador.
    app.include_router(health.router, prefix=API_PREFIX)

    api = APIRouter(prefix=API_PREFIX, dependencies=[Depends(general_rate_limit)])
    api.include_router(public_config.router)
    api.include_router(auth.router)
    api.include_router(colaboradores.router)
    api.include_router(descansos.router)
    api.include_router(analisis.router)
    api.include_router(llm.router)
    api.include_router(demo_api.router)
    app.include_router(api)
    return app
