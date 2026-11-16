"""Descansos médicos: alta, consulta, decisión, borrado y documentos."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Query, Request, Response
from starlette.datastructures import UploadFile

from humanaiz.api.deps import ClientIp, LimiterDep, SessionDep, SettingsDep, StorageDep
from humanaiz.api.schemas import DecisionRequest, Descanso, EstadoDescanso, Pagina
from humanaiz.errors import invalido
from humanaiz.security.deps import CurrentUser, RRHHUser
from humanaiz.security.ratelimit import client_ip
from humanaiz.services import descansos as servicio

router = APIRouter(tags=["descansos"])

Limit = Annotated[int, Query(ge=1, le=200)]
Offset = Annotated[int, Query(ge=0)]

# Los documentos nunca se interpretan en el origen de la aplicación.
_CSP_DOCUMENTO = "sandbox; default-src 'none'"

_CUERPO_ALTA = {
    "requestBody": {
        "required": True,
        "content": {
            "multipart/form-data": {
                "schema": {
                    "type": "object",
                    "required": ["archivo"],
                    "properties": {
                        "archivo": {
                            "type": "string",
                            "format": "binary",
                            "description": "Imagen del certificado médico: JPG, PNG o WebP.",
                        },
                        "sede": {
                            "type": "string",
                            "maxLength": servicio.SEDE_MAX,
                            "description": "Si se omite se usa la sede del colaborador.",
                        },
                    },
                }
            }
        },
    }
}


@router.post("/descansos", status_code=201, response_model=Descanso, openapi_extra=_CUERPO_ALTA)
async def crear_descanso(
    request: Request,
    principal: CurrentUser,
    session: SessionDep,
    settings: SettingsDep,
    storage: StorageDep,
    limiter: LimiterDep,
    ip: ClientIp,
) -> Descanso:
    # El formulario no se declara como parámetro a propósito: así la
    # autenticación, los límites de uso y las cuotas se comprueban ANTES de leer
    # (y volcar a disco) el cuerpo de la petición.
    await limiter.check_en_capas(
        "upload",
        limite=settings.rate_limit_upload,
        usuario=principal.limit_key,
        ip=client_ip(request),
        limite_global=settings.rate_limit_upload_global,
    )
    await servicio.check_puede_subir(session, storage, settings, principal)

    form = await request.form(max_files=1, max_fields=4, max_part_size=4096)
    try:
        archivo = form.get("archivo")
        if not isinstance(archivo, UploadFile):
            raise invalido("archivo_invalido", "Adjunta el certificado médico.", campo="archivo")
        data = await archivo.read()
        sede = form.get("sede")
    finally:
        await form.close()

    descanso_id = await servicio.crear(
        session,
        storage,
        settings,
        principal,
        data=data,
        sede=sede if isinstance(sede, str) else None,
        ip=ip,
        normalize_slots=request.app.state.normalize_slots,
    )
    descanso = await servicio.get_visible(session, principal, descanso_id)
    return await servicio.serialize_one(session, settings, principal, descanso)


@router.get("/me/descansos", response_model=Pagina[Descanso])
async def mis_descansos(
    principal: CurrentUser,
    session: SessionDep,
    settings: SettingsDep,
    estado: EstadoDescanso | None = None,
    limit: Limit = 50,
    offset: Offset = 0,
) -> Pagina[Descanso]:
    filas, total = await servicio.listar_propios(
        session, principal, estado=estado, limit=limit, offset=offset
    )
    items = await servicio.serialize(session, settings, principal, filas)
    return Pagina[Descanso](items=items, total=total, limit=limit, offset=offset)


@router.get("/descansos", response_model=Pagina[Descanso])
async def todos_los_descansos(
    principal: RRHHUser,
    session: SessionDep,
    settings: SettingsDep,
    estado: EstadoDescanso | None = None,
    dni: Annotated[str | None, Query(pattern=r"^[0-9]{1,8}$")] = None,
    sede: Annotated[str | None, Query(max_length=servicio.SEDE_MAX)] = None,
    limit: Limit = 50,
    offset: Offset = 0,
) -> Pagina[Descanso]:
    filas, total = await servicio.listar_todos(
        session, principal, estado=estado, dni=dni, sede=sede, limit=limit, offset=offset
    )
    items = await servicio.serialize(session, settings, principal, filas)
    return Pagina[Descanso](items=items, total=total, limit=limit, offset=offset)


@router.get("/descansos/{descanso_id}", response_model=Descanso)
async def obtener_descanso(
    descanso_id: uuid.UUID, principal: CurrentUser, session: SessionDep, settings: SettingsDep
) -> Descanso:
    descanso = await servicio.get_visible(session, principal, descanso_id)
    return await servicio.serialize_one(session, settings, principal, descanso)


@router.delete("/descansos/{descanso_id}", status_code=204)
async def eliminar_descanso(
    descanso_id: uuid.UUID,
    principal: CurrentUser,
    session: SessionDep,
    storage: StorageDep,
    ip: ClientIp,
) -> Response:
    await servicio.eliminar(session, storage, principal, descanso_id, ip=ip)
    return Response(status_code=204)


@router.post("/descansos/{descanso_id}/decision", response_model=Descanso)
async def decidir_descanso(
    descanso_id: uuid.UUID,
    payload: DecisionRequest,
    principal: RRHHUser,
    session: SessionDep,
    settings: SettingsDep,
    ip: ClientIp,
) -> Descanso:
    descanso = await servicio.decidir(
        session,
        principal,
        descanso_id,
        estado=payload.estado,
        comentario=payload.comentario_rrhh,
        fecha_inicio=payload.fecha_inicio,
        fecha_fin=payload.fecha_fin,
        ip=ip,
    )
    return await servicio.serialize_one(session, settings, principal, descanso)


@router.get(
    "/descansos/{descanso_id}/archivo",
    response_class=Response,
    responses={200: {"content": {"image/jpeg": {}}}},
)
async def descargar_imagen(
    descanso_id: uuid.UUID,
    principal: CurrentUser,
    session: SessionDep,
    storage: StorageDep,
    ip: ClientIp,
) -> Response:
    """Imagen guardada (la re-codificación del servidor), siempre como descarga."""
    data, descanso = await servicio.descargar_imagen(
        session, storage, principal, descanso_id, ip=ip
    )
    nombre = f"certificado-{str(descanso.id)[:8]}.jpg"
    return Response(
        content=data,
        media_type="image/jpeg",
        headers={
            "Content-Disposition": f'attachment; filename="{nombre}"',
            "Content-Security-Policy": _CSP_DOCUMENTO,
        },
    )


@router.get(
    "/descansos/{descanso_id}/paginas/{numero}",
    response_class=Response,
    responses={200: {"content": {"image/jpeg": {}}}},
)
async def ver_pagina(
    descanso_id: uuid.UUID,
    numero: int,
    principal: CurrentUser,
    session: SessionDep,
    storage: StorageDep,
) -> Response:
    """Página re-codificada por el servidor (JPEG sin metadatos), para mostrar en pantalla."""
    data = await servicio.leer_pagina(session, storage, principal, descanso_id, numero)
    return Response(
        content=data,
        media_type="image/jpeg",
        headers={"Content-Security-Policy": _CSP_DOCUMENTO},
    )
