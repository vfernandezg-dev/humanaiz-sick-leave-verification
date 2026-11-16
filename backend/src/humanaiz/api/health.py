"""Sondas de vida y de disponibilidad."""

from __future__ import annotations

import logging
from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse

from humanaiz.db import Database, get_db

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/health", tags=["salud"])


@router.get("/live")
async def live() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/ready", include_in_schema=False)
async def ready(db: Annotated[Database, Depends(get_db)]) -> JSONResponse:
    try:
        await db.ping()
    except Exception:
        logger.warning("la base de datos no responde", exc_info=True)
        return JSONResponse({"status": "sin_base_de_datos"}, status_code=503)
    return JSONResponse({"status": "ok"})
