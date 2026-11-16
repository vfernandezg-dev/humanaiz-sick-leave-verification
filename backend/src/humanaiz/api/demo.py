"""Recursos de la demostración: certificados de ejemplo para probar la lectura con IA."""

from __future__ import annotations

import asyncio
from datetime import datetime
from typing import Literal
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Response

from humanaiz.api.deps import LimiterDep, SettingsDep
from humanaiz.errors import conflicto, no_encontrado
from humanaiz.security.deps import CurrentUser
from humanaiz.services import certificados

router = APIRouter(prefix="/demo", tags=["demo"])

_TIPOS = {"jpg": "image/jpeg", "pdf": "application/pdf"}


@router.get(
    "/certificados/{variante}",
    response_class=Response,
    responses={200: {"content": {"image/jpeg": {}, "application/pdf": {}}}},
)
async def certificado_de_ejemplo(
    variante: certificados.Variante,
    principal: CurrentUser,
    settings: SettingsDep,
    limiter: LimiterDep,
    formato: Literal["jpg", "pdf"] = "jpg",
) -> Response:
    """Genera un certificado ficticio con los datos del propio usuario.

    Solo existe en modo demo: los datos de las cuentas de prueba son inventados.
    Variantes: `valido` (coincide con la ficha), `observado` (días que no cuadran
    y sin CMP), `otra-persona` (a nombre de otra persona) y `citt`.
    """
    if not settings.demo_mode:
        raise no_encontrado()
    if principal.colaborador_id is None:
        raise conflicto(
            "sin_colaborador_vinculado", "Tu cuenta no está vinculada a una ficha de colaborador."
        )
    await limiter.check(settings.rate_limit_upload, "ejemplo", principal.limit_key)

    hoy = datetime.now(ZoneInfo(settings.tz_negocio)).date()
    datos = certificados.variante(
        variante,
        certificados.base_para(
            nombres=principal.nombres, apellidos=principal.apellidos, dni=principal.dni, hoy=hoy
        ),
    )
    contenido = await asyncio.to_thread(
        lambda: certificados.exportar(certificados.renderizar(datos), formato)
    )
    return Response(
        content=contenido,
        media_type=_TIPOS[formato],
        headers={
            "Content-Disposition": (
                f'attachment; filename="certificado-ejemplo-{variante}.{formato}"'
            ),
            "Content-Security-Policy": "sandbox; default-src 'none'",
        },
    )
