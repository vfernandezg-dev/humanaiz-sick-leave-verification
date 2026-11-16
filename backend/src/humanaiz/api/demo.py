"""Recursos de la demostración: certificados de ejemplo para probar la lectura con IA."""

from __future__ import annotations

import asyncio
from datetime import datetime
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Request, Response

from humanaiz.api.deps import LimiterDep, SettingsDep
from humanaiz.errors import conflicto, no_encontrado
from humanaiz.security.deps import CurrentUser
from humanaiz.security.ratelimit import client_ip
from humanaiz.services import certificados

router = APIRouter(prefix="/demo", tags=["demo"])


@router.get(
    "/certificados/{variante}",
    response_class=Response,
    responses={200: {"content": {"image/jpeg": {}}}},
)
async def certificado_de_ejemplo(
    variante: certificados.Variante,
    request: Request,
    principal: CurrentUser,
    settings: SettingsDep,
    limiter: LimiterDep,
) -> Response:
    """Genera un certificado ficticio (JPEG) con los datos del propio usuario.

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
    # Generarlo cuesta CPU: mismos topes que una subida, con contadores propios.
    await limiter.check_en_capas(
        "ejemplo",
        limite=settings.rate_limit_upload,
        usuario=principal.limit_key,
        ip=client_ip(request),
        limite_global=settings.rate_limit_upload_global,
    )

    hoy = datetime.now(ZoneInfo(settings.tz_negocio)).date()
    datos = certificados.variante(
        variante,
        certificados.base_para(
            nombres=principal.nombres, apellidos=principal.apellidos, dni=principal.dni, hoy=hoy
        ),
    )
    contenido = await asyncio.to_thread(
        lambda: certificados.exportar(certificados.renderizar(datos), "jpg")
    )
    return Response(
        content=contenido,
        media_type="image/jpeg",
        headers={
            "Content-Disposition": f'attachment; filename="certificado-ejemplo-{variante}.jpg"',
            "Content-Security-Policy": "sandbox; default-src 'none'",
        },
    )
