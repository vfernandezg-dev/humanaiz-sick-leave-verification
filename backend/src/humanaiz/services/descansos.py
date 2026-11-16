"""Descansos médicos: alta con documento, consulta, decisión y borrado.

Toda regla de visibilidad y de permisos vive aquí, en el servidor. El frontend
recibe `permisos` ya calculados y no las reimplementa.
"""

from __future__ import annotations

import asyncio
import hashlib
import logging
import uuid
from collections.abc import Sequence
from datetime import UTC, date, datetime, timedelta

from sqlalchemy import ColumnElement, delete, func, or_, select, update
from sqlalchemy.dialects.postgresql import distinct_on
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import contains_eager

from humanaiz.api import schemas
from humanaiz.config import Settings
from humanaiz.errors import AppError, conflicto, invalido, no_encontrado, prohibido
from humanaiz.models import AnalisisDescanso, Colaborador, DescansoMedico
from humanaiz.scanning.errors import DocumentoInvalido
from humanaiz.scanning.preprocess import Limits, normalize
from humanaiz.scanning.sniff import looks_like_heic, looks_like_pdf, sniff
from humanaiz.security.deps import Principal
from humanaiz.services import audit
from humanaiz.storage.base import ObjetoNoEncontrado, Storage, page_name

logger = logging.getLogger(__name__)

PENDIENTE = "Pendiente"
SEDE_MAX = 100
_MB = 1024 * 1024


# ---------- visibilidad y permisos ----------


def visible_filter(principal: Principal) -> list[ColumnElement[bool]]:
    """Condiciones SQL de lo que el usuario puede ver, además de su rol.

    En la demo las cuentas son compartidas: cada visitante ve las muestras y lo
    que subió su propio navegador, nunca lo de otros visitantes.
    """
    if principal.is_demo:
        return [
            or_(
                DescansoMedico.es_muestra.is_(True),
                DescansoMedico.visitor_id == principal.visitor_id,
            )
        ]
    return []


def es_propio(descanso: DescansoMedico, principal: Principal) -> bool:
    return (
        principal.colaborador_id is not None and descanso.colaborador_id == principal.colaborador_id
    )


def permisos(descanso: DescansoMedico, principal: Principal) -> schemas.DescansoPermisos:
    propio = es_propio(descanso, principal)
    # Las muestras de la demo son de solo lectura para todos.
    editable = descanso.estado == PENDIENTE and not descanso.es_muestra
    return schemas.DescansoPermisos(
        puede_analizar=editable and (propio or principal.es_rrhh),
        # Nadie decide sobre su propio descanso, tampoco un analista de RRHH.
        puede_decidir=editable and principal.es_rrhh and not propio,
        puede_eliminar=editable and propio,
    )


async def get_visible(
    session: AsyncSession, principal: Principal, descanso_id: uuid.UUID
) -> DescansoMedico:
    """Devuelve el descanso o 404. Lo que no se puede ver "no existe"."""
    descanso = await session.scalar(
        select(DescansoMedico).where(DescansoMedico.id == descanso_id, *visible_filter(principal))
    )
    if descanso is None or not (principal.es_rrhh or es_propio(descanso, principal)):
        raise no_encontrado("No se encontró el descanso médico.")
    return descanso


# ---------- serialización ----------


def analisis_to_schema(row: AnalisisDescanso) -> schemas.Analisis:
    resultado = row.resultado or {}
    uso = None
    if row.tokens_entrada is not None or row.tokens_salida is not None:
        uso = schemas.UsoTokens(tokens_entrada=row.tokens_entrada, tokens_salida=row.tokens_salida)
    return schemas.Analisis(
        id=row.id,
        created_at=row.finished_at or row.started_at,
        proveedor=row.proveedor,
        modelo=row.modelo_efectivo or row.modelo,
        solicitado_por=schemas.Solicitante(
            id=row.solicitante.id,
            nombres=row.solicitante.nombres,
            apellidos=row.solicitante.apellidos,
            role=row.solicitante.role,  # type: ignore[arg-type]
        ),
        estado_documento=row.estado_documento,  # type: ignore[arg-type]
        extraidos=schemas.Extraidos.model_validate(resultado.get("extraidos", {})),
        validaciones=resultado.get("validaciones", {}),
        validaciones_detalle=resultado.get("validaciones_detalle", []),
        motivos_rechazo=resultado.get("motivos_rechazo", []),
        comentario_general=resultado.get("comentario_general", ""),
        uso=uso,
        duracion_ms=row.duracion_ms,
        version_prompt=row.version_prompt,
        version_reglas=row.version_reglas,
    )


def to_schema(
    descanso: DescansoMedico,
    principal: Principal,
    *,
    ultimo: AnalisisDescanso | None,
    en_curso: bool,
) -> schemas.Descanso:
    colaborador = descanso.colaborador
    return schemas.Descanso(
        id=descanso.id,
        estado=descanso.estado,  # type: ignore[arg-type]
        sede=descanso.sede,
        fecha_inicio=descanso.fecha_inicio,
        fecha_fin=descanso.fecha_fin,
        comentario_rrhh=descanso.comentario_rrhh,
        created_at=descanso.created_at,
        updated_at=descanso.updated_at,
        decidido_at=descanso.decidido_at,
        colaborador=schemas.DescansoColaborador(
            id=colaborador.id,
            dni=colaborador.dni,
            nombres=colaborador.nombres,
            apellidos=colaborador.apellidos,
        ),
        archivo=schemas.DescansoArchivo(
            mime=descanso.archivo_mime,
            size_bytes=descanso.archivo_size,
            paginas=descanso.paginas,
        ),
        ultimo_analisis=analisis_to_schema(ultimo) if ultimo else None,
        analisis_en_curso=en_curso,
        es_muestra=descanso.es_muestra,
        es_propio=es_propio(descanso, principal),
        permisos=permisos(descanso, principal),
    )


def stale_before(settings: Settings) -> datetime:
    """Un análisis en proceso más antiguo que esto se considera abandonado."""
    return datetime.now(UTC) - timedelta(seconds=settings.analysis_deadline_seconds + 30)


async def serialize(
    session: AsyncSession,
    settings: Settings,
    principal: Principal,
    descansos: Sequence[DescansoMedico],
) -> list[schemas.Descanso]:
    if not descansos:
        return []
    ids = [d.id for d in descansos]
    ultimos = (
        await session.scalars(
            select(AnalisisDescanso)
            .where(AnalisisDescanso.descanso_id.in_(ids), AnalisisDescanso.estado == "completado")
            .ext(distinct_on(AnalisisDescanso.descanso_id))
            .order_by(AnalisisDescanso.descanso_id, AnalisisDescanso.started_at.desc())
        )
    ).all()
    por_descanso = {a.descanso_id: a for a in ultimos}
    en_curso = set(
        await session.scalars(
            select(AnalisisDescanso.descanso_id).where(
                AnalisisDescanso.descanso_id.in_(ids),
                AnalisisDescanso.estado == "en_proceso",
                AnalisisDescanso.started_at > stale_before(settings),
            )
        )
    )
    return [
        to_schema(d, principal, ultimo=por_descanso.get(d.id), en_curso=d.id in en_curso)
        for d in descansos
    ]


async def serialize_one(
    session: AsyncSession, settings: Settings, principal: Principal, descanso: DescansoMedico
) -> schemas.Descanso:
    return (await serialize(session, settings, principal, [descanso]))[0]


# ---------- listados ----------


def _like(texto: str) -> str:
    escapado = texto.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return f"%{escapado}%"


async def _paginar(
    session: AsyncSession,
    condiciones: list[ColumnElement[bool]],
    *,
    limit: int,
    offset: int,
) -> tuple[list[DescansoMedico], int]:
    total = (
        await session.scalar(
            select(func.count(DescansoMedico.id))
            .join(DescansoMedico.colaborador)
            .where(*condiciones)
        )
        or 0
    )
    filas = (
        await session.scalars(
            select(DescansoMedico)
            .join(DescansoMedico.colaborador)
            .options(contains_eager(DescansoMedico.colaborador))
            .where(*condiciones)
            .order_by(DescansoMedico.created_at.desc(), DescansoMedico.id)
            .limit(limit)
            .offset(offset)
        )
    ).all()
    return list(filas), total


async def listar_propios(
    session: AsyncSession,
    principal: Principal,
    *,
    estado: str | None,
    limit: int,
    offset: int,
) -> tuple[list[DescansoMedico], int]:
    if principal.colaborador_id is None:
        return [], 0
    condiciones = [
        DescansoMedico.colaborador_id == principal.colaborador_id,
        *visible_filter(principal),
    ]
    if estado:
        condiciones.append(DescansoMedico.estado == estado)
    return await _paginar(session, condiciones, limit=limit, offset=offset)


async def listar_todos(
    session: AsyncSession,
    principal: Principal,
    *,
    estado: str | None,
    dni: str | None,
    sede: str | None,
    limit: int,
    offset: int,
) -> tuple[list[DescansoMedico], int]:
    condiciones = visible_filter(principal)
    if estado:
        condiciones.append(DescansoMedico.estado == estado)
    if dni:
        condiciones.append(Colaborador.dni.like(_like(dni), escape="\\"))
    if sede:
        condiciones.append(DescansoMedico.sede.ilike(_like(sede), escape="\\"))
    return await _paginar(session, condiciones, limit=limit, offset=offset)


# ---------- alta ----------


def _sede_valida(sede: str | None, principal: Principal) -> str:
    valor = (sede or "").strip() or (principal.colaborador_sede or "").strip()
    if not valor:
        raise invalido("validacion", "Indica la sede.", campo="sede")
    if len(valor) > SEDE_MAX:
        raise invalido("validacion", f"La sede admite hasta {SEDE_MAX} caracteres.", campo="sede")
    return valor


async def check_puede_subir(
    session: AsyncSession, storage: Storage, settings: Settings, principal: Principal
) -> None:
    """Comprobaciones baratas, antes de leer el cuerpo de la petición."""
    if principal.colaborador_id is None or not principal.colaborador_activo:
        raise conflicto(
            "sin_colaborador_vinculado",
            "Tu cuenta no está vinculada a una ficha de colaborador activa. Contacta con RRHH.",
        )
    if principal.is_demo:
        cargados = await session.scalar(
            select(func.count())
            .select_from(DescansoMedico)
            .where(DescansoMedico.visitor_id == principal.visitor_id)
        )
        if (cargados or 0) >= settings.demo_max_descansos_per_visitor:
            raise conflicto(
                "limite_demo",
                "Alcanzaste el máximo de documentos de la demo. Elimina alguno para subir otro.",
            )
    lleno = await storage.free_bytes() < settings.min_free_disk_mb * _MB
    if not lleno and settings.storage_max_mb:
        # `archivo_size` es lo que ocupa en disco la imagen guardada.
        ocupado = await session.scalar(
            select(func.coalesce(func.sum(DescansoMedico.archivo_size), 0))
        )
        lleno = (ocupado or 0) >= settings.storage_max_mb * _MB
    if lleno:
        raise AppError(
            503,
            "almacenamiento_lleno",
            "No hay espacio para recibir documentos en este momento. Inténtalo más tarde.",
        )
    # Libera la conexión: lo que sigue (leer y normalizar el archivo) puede tardar.
    await session.commit()


def limites_imagen(settings: Settings) -> Limits:
    return Limits(
        max_pixels=settings.max_image_pixels,
        min_side_px=settings.min_image_side_px,
        page_max_side_px=settings.page_max_side_px,
        timeout_seconds=settings.normalize_timeout_seconds,
    )


def _motivo_no_admitido(head: bytes) -> str:
    if looks_like_heic(head):
        return (
            "Las fotos en formato HEIC no se admiten. Conviértela a JPG "
            "(o comparte la foto como 'Más compatible') y vuelve a subirla."
        )
    if looks_like_pdf(head):
        return (
            "Los PDF no se admiten. Sube una foto o una captura del certificado (JPG, PNG o WebP)."
        )
    return "Formato no admitido. Solo se aceptan imágenes JPG, PNG o WebP."


async def crear(
    session: AsyncSession,
    storage: Storage,
    settings: Settings,
    principal: Principal,
    *,
    data: bytes,
    sede: str | None,
    ip: str | None,
    normalize_slots: asyncio.Semaphore,
) -> uuid.UUID:
    """Valida, normaliza y guarda la imagen. Devuelve el id del descanso creado.

    Del archivo recibido solo se conserva su huella (sha256), para detectar
    duplicados. Lo que se guarda es la re-codificación hecha por el servidor:
    nada de lo que el archivo original llevara aparte de los píxeles se almacena.
    """
    sede_final = _sede_valida(sede, principal)
    if not data:
        raise invalido("archivo_invalido", "Adjunta el certificado médico.", campo="archivo")
    if len(data) > settings.max_upload_bytes:
        raise AppError(
            413,
            "archivo_demasiado_grande",
            f"La imagen supera el máximo de {settings.max_upload_bytes // _MB} MB.",
        )
    # El tipo se decide por el contenido; se ignoran Content-Type y nombre.
    kind = sniff(data[:16])
    if kind is None:
        raise AppError(415, "tipo_no_soportado", _motivo_no_admitido(data[:16]))

    try:
        async with normalize_slots:
            documento = await normalize(data, kind, limites_imagen(settings))
    except DocumentoInvalido as exc:
        raise AppError(422, exc.code, exc.message) from None

    prefix = storage.new_prefix()
    descanso = DescansoMedico(
        colaborador_id=principal.colaborador_id,
        created_by=principal.id,
        sede=sede_final,
        archivo_key=prefix,
        archivo_mime=kind.value,
        archivo_size=sum(len(p) for p in documento.pages),
        archivo_sha256=hashlib.sha256(data).digest(),
        paginas=len(documento.pages),
        visitor_id=principal.visitor_id if principal.is_demo else None,
    )
    try:
        for numero, pagina in enumerate(documento.pages, start=1):
            await storage.put(prefix, page_name(numero), pagina)
        session.add(descanso)
        await session.flush()
        audit.record(
            session,
            "descanso_creado",
            actor_id=principal.id,
            entidad="descanso",
            entidad_id=descanso.id,
            ip=ip,
            detalle={"mime": kind.value, "paginas": len(documento.pages)},
        )
        await session.commit()
    except BaseException:
        # Sin fila en la base no debe quedar archivo: se limpia lo ya escrito.
        await session.rollback()
        await storage.delete_prefix(prefix)
        raise
    return descanso.id


# ---------- decisión y borrado ----------


async def decidir(
    session: AsyncSession,
    principal: Principal,
    descanso_id: uuid.UUID,
    *,
    estado: str,
    comentario: str | None,
    fecha_inicio: date | None,
    fecha_fin: date | None,
    ip: str | None,
) -> DescansoMedico:
    descanso = await get_visible(session, principal, descanso_id)
    if descanso.es_muestra:
        raise prohibido("Las muestras de la demo son de solo lectura.")
    if es_propio(descanso, principal):
        raise AppError(
            403, "decision_propia_no_permitida", "No puedes decidir sobre tu propio descanso."
        )
    if descanso.estado != PENDIENTE:
        raise conflicto("descanso_ya_decidido", "Este descanso ya fue decidido.")

    comentario = (comentario or "").strip() or None
    inicio = fecha_inicio or descanso.fecha_inicio
    fin = fecha_fin or descanso.fecha_fin
    if estado == "Rechazado" and not comentario:
        raise invalido(
            "comentario_requerido",
            "Explica el motivo del rechazo: el colaborador lo verá.",
            campo="comentario_rrhh",
        )
    if estado == "Aprobado" and (inicio is None or fin is None):
        raise invalido(
            "fechas_requeridas",
            "Indica las fechas de inicio y fin del descanso para aprobarlo.",
            campo="fecha_inicio",
        )
    if inicio is not None and fin is not None and fin < inicio:
        raise invalido(
            "validacion",
            "La fecha de fin no puede ser anterior a la de inicio.",
            campo="fecha_fin",
        )

    # El WHERE estado = 'Pendiente' hace atómica la decisión: de dos
    # analistas que deciden a la vez, solo uno la registra.
    resultado = await session.execute(
        update(DescansoMedico)
        .where(DescansoMedico.id == descanso.id, DescansoMedico.estado == PENDIENTE)
        .values(
            estado=estado,
            comentario_rrhh=comentario,
            fecha_inicio=inicio,
            fecha_fin=fin,
            decidido_por=principal.id,
            decidido_at=datetime.now(UTC),
        )
        .returning(DescansoMedico.id)
    )
    if resultado.scalar_one_or_none() is None:
        await session.rollback()
        raise conflicto("descanso_ya_decidido", "Este descanso ya fue decidido.")
    audit.record(
        session,
        "descanso_decidido",
        actor_id=principal.id,
        entidad="descanso",
        entidad_id=descanso.id,
        ip=ip,
        detalle={"estado": estado},
    )
    await session.commit()
    await session.refresh(descanso)
    return descanso


async def eliminar(
    session: AsyncSession,
    storage: Storage,
    principal: Principal,
    descanso_id: uuid.UUID,
    *,
    ip: str | None,
) -> None:
    descanso = await get_visible(session, principal, descanso_id)
    if descanso.es_muestra:
        raise prohibido("Las muestras de la demo son de solo lectura.")
    if not es_propio(descanso, principal):
        raise prohibido("Solo quien registró el descanso puede eliminarlo.")
    resultado = await session.execute(
        delete(DescansoMedico)
        .where(DescansoMedico.id == descanso.id, DescansoMedico.estado == PENDIENTE)
        .returning(DescansoMedico.archivo_key)
    )
    prefix = resultado.scalar_one_or_none()
    if prefix is None:
        await session.rollback()
        raise conflicto(
            "descanso_no_pendiente", "Solo se puede eliminar un descanso que sigue pendiente."
        )
    audit.record(
        session,
        "descanso_eliminado",
        actor_id=principal.id,
        entidad="descanso",
        entidad_id=descanso_id,
        ip=ip,
    )
    await session.commit()
    await storage.delete_prefix(prefix)


# ---------- archivos ----------


async def descargar_imagen(
    session: AsyncSession,
    storage: Storage,
    principal: Principal,
    descanso_id: uuid.UUID,
    *,
    ip: str | None,
) -> tuple[bytes, DescansoMedico]:
    descanso = await get_visible(session, principal, descanso_id)
    audit.record(
        session,
        "archivo_descargado",
        actor_id=principal.id,
        entidad="descanso",
        entidad_id=descanso.id,
        ip=ip,
    )
    await session.commit()
    try:
        return await storage.get(descanso.archivo_key, page_name(1)), descanso
    except ObjetoNoEncontrado:
        logger.error("falta la imagen del descanso %s", descanso.id)
        raise no_encontrado("El documento ya no está disponible.") from None


async def leer_pagina(
    session: AsyncSession,
    storage: Storage,
    principal: Principal,
    descanso_id: uuid.UUID,
    numero: int,
) -> bytes:
    descanso = await get_visible(session, principal, descanso_id)
    if not 1 <= numero <= descanso.paginas:
        raise no_encontrado("Esa página no existe.")
    await session.commit()
    try:
        return await storage.get(descanso.archivo_key, page_name(numero))
    except ObjetoNoEncontrado:
        logger.error("falta la página %s del descanso %s", numero, descanso.id)
        raise no_encontrado("El documento ya no está disponible.") from None
