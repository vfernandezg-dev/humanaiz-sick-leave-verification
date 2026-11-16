"""Análisis con IA de un descanso, con la clave del propio usuario (BYOK)."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Request

from humanaiz.api.deps import ClientIp, DbDep, LimiterDep, SettingsDep, StorageDep
from humanaiz.api.schemas import Analisis, AnalisisRequest
from humanaiz.security.deps import CurrentUser
from humanaiz.security.llm_key import LLM_KEY_HEADER, read_llm_key
from humanaiz.security.ratelimit import client_ip
from humanaiz.services import analisis as servicio
from humanaiz.services.descansos import analisis_to_schema

router = APIRouter(tags=["análisis"])

_CABECERA_CLAVE = {
    "parameters": [
        {
            "name": LLM_KEY_HEADER,
            "in": "header",
            "required": True,
            "schema": {"type": "string"},
            "description": (
                "Clave de API del proveedor de IA, del propio usuario. Se usa solo para "
                "esta petición y no se almacena."
            ),
        }
    ]
}


@router.post(
    "/descansos/{descanso_id}/analisis",
    status_code=201,
    response_model=Analisis,
    openapi_extra=_CABECERA_CLAVE,
)
async def analizar_descanso(
    descanso_id: uuid.UUID,
    payload: AnalisisRequest,
    request: Request,
    principal: CurrentUser,
    settings: SettingsDep,
    db: DbDep,
    storage: StorageDep,
    limiter: LimiterDep,
    ip: ClientIp,
) -> Analisis:
    # Sin sesión de base de datos con vida de petición: el servicio abre y
    # cierra las suyas para no retener una conexión mientras responde el proveedor.
    api_key = read_llm_key(request)
    # Sin tope total: cada análisis lo paga la clave de quien lo pide, y la carga
    # del servidor ya la acota ANALYSIS_MAX_CONCURRENCY.
    await limiter.check_en_capas(
        "analisis",
        limite=settings.rate_limit_analysis,
        usuario=principal.limit_key,
        ip=client_ip(request),
    )
    fila = await servicio.analizar(
        db,
        storage,
        settings,
        principal,
        descanso_id,
        proveedor=payload.proveedor.strip().lower(),
        modelo=payload.modelo,
        api_key=api_key,
        ip=ip,
        slots=request.app.state.analysis_slots,
        en_vuelo=request.app.state.analisis_en_vuelo,
    )
    return analisis_to_schema(fila)


@router.get("/descansos/{descanso_id}/analisis", response_model=list[Analisis])
async def historial_de_analisis(
    descanso_id: uuid.UUID, principal: CurrentUser, db: DbDep
) -> list[Analisis]:
    """Análisis completados de un descanso, del más reciente al más antiguo."""
    return [analisis_to_schema(f) for f in await servicio.listar(db, principal, descanso_id)]
