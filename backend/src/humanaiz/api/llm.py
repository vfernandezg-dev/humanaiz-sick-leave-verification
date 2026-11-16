"""Utilidades de IA: comprobar una clave y listar los modelos que ofrece."""

from __future__ import annotations

import asyncio

from fastapi import APIRouter, Request

from humanaiz.api.deps import LimiterDep, SettingsDep
from humanaiz.api.schemas import ModeloDisponibleSalida, ModelosDisponibles, ModelosRequest
from humanaiz.errors import invalido
from humanaiz.scanning import engine
from humanaiz.scanning.catalog import get_provider
from humanaiz.scanning.errors import ProviderError, TiempoAgotado
from humanaiz.security.deps import CurrentUser
from humanaiz.security.llm_key import LLM_KEY_HEADER, read_llm_key
from humanaiz.security.ratelimit import client_ip
from humanaiz.services.analisis import to_app_error

router = APIRouter(prefix="/llm", tags=["análisis"])

# Listar modelos es una llamada corta: el proxy corta las peticiones de /api a los 30 s.
_TIMEOUT_S = 20
_PLAZO_S = 25


@router.post(
    "/modelos",
    response_model=ModelosDisponibles,
    openapi_extra={
        "parameters": [
            {
                "name": LLM_KEY_HEADER,
                "in": "header",
                "required": True,
                "schema": {"type": "string"},
                "description": "Clave del proveedor de IA. Se usa solo para esta consulta.",
            }
        ]
    },
)
async def modelos_disponibles(
    payload: ModelosRequest,
    request: Request,
    principal: CurrentUser,
    settings: SettingsDep,
    limiter: LimiterDep,
) -> ModelosDisponibles:
    """Comprueba la clave y devuelve los modelos que puede usar, sugeridos primero.

    La clave no se guarda: viaja en la cabecera, se usa para esta consulta y se
    descarta, igual que en el análisis.
    """
    api_key = read_llm_key(request)
    proveedor = payload.proveedor.strip().lower()
    info = get_provider(proveedor)
    if info is None or proveedor not in settings.llm_enabled_providers:
        raise invalido(
            "llm_proveedor_no_soportado", "Ese proveedor de IA no está disponible.", "proveedor"
        )
    # Límite estricto: sin él, este endpoint serviría para probar claves robadas.
    # El tope total impide hacerlo a escala rotando IPs o navegadores.
    await limiter.check_en_capas(
        "modelos",
        limite=settings.rate_limit_modelos,
        usuario=principal.limit_key,
        ip=client_ip(request),
        limite_global=settings.rate_limit_modelos_global,
    )

    try:
        async with asyncio.timeout(_PLAZO_S):
            disponibles = await engine.listar_modelos(
                provider=proveedor, api_key=api_key, timeout_s=_TIMEOUT_S
            )
    except TimeoutError:
        raise to_app_error(TiempoAgotado("El proveedor tardó demasiado.")) from None
    except ProviderError as exc:
        raise to_app_error(exc) from None

    sugeridos = [m.id for m in info.modelos]
    por_id = {m.id: m for m in disponibles}
    salida = [
        ModeloDisponibleSalida(
            id=modelo.id,
            nombre=por_id[modelo.id].nombre if modelo.id in por_id else modelo.nombre,
            sugerido=True,
        )
        for modelo in info.modelos
        if modelo.id in por_id
    ]
    salida += [
        ModeloDisponibleSalida(id=m.id, nombre=m.nombre, sugerido=False)
        for m in disponibles
        if m.id not in sugeridos
    ]
    return ModelosDisponibles(proveedor=proveedor, modelos=salida)
