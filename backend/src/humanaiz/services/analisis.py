"""Análisis de un descanso con la clave de IA del usuario (BYOK).

La petición se ejecuta en tres fases para no retener una conexión de base de
datos durante los 30-90 s que tarda el proveedor:

1. Reservar: transacción corta que valida y deja una fila `en_proceso`. Un
   índice único parcial garantiza un solo análisis en curso por descanso.
2. Llamar: sin conexión abierta. Es el único tramo donde existe la clave.
3. Persistir: transacción corta que evalúa las reglas y guarda el resultado.

El análisis nunca modifica el descanso (ni fechas ni estado): es una
sugerencia para quien decide.
"""

from __future__ import annotations

import asyncio
import logging
import time
import uuid
from dataclasses import dataclass
from datetime import UTC, date, datetime
from zoneinfo import ZoneInfo

from pydantic import SecretStr
from sqlalchemy import func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from humanaiz.config import Settings
from humanaiz.db import Database
from humanaiz.errors import AppError, conflicto, invalido, no_encontrado, prohibido
from humanaiz.models import AnalisisDescanso, DescansoMedico
from humanaiz.scanning import engine
from humanaiz.scanning.catalog import get_provider
from humanaiz.scanning.errors import ProviderError, TiempoAgotado
from humanaiz.scanning.prompt import PROMPT_VERSION
from humanaiz.scanning.rules import RULES_VERSION
from humanaiz.scanning.types import ContextoValidacion, ExtractionOutcome
from humanaiz.security.deps import Principal
from humanaiz.services import audit
from humanaiz.services.descansos import PENDIENTE, get_visible, stale_before, visible_filter
from humanaiz.storage.base import ObjetoNoEncontrado, Storage, page_name

logger = logging.getLogger(__name__)

_RETRY_AFTER_MAX = 120

# Código del motor -> (estado HTTP, mensaje para el usuario). Los problemas con
# la clave de IA nunca devuelven 401: ese código es solo de la sesión propia.
_ERRORES_LLM: dict[str, tuple[int, str]] = {
    "llm_clave_invalida": (
        400,
        "El proveedor rechazó tu clave de IA. Comprueba que sea correcta y esté activa.",
    ),
    "llm_sin_acceso_modelo": (
        400,
        "Tu clave no tiene acceso a ese modelo. Elige otro modelo o revisa tu cuenta.",
    ),
    "llm_sin_saldo": (
        402,
        "Tu cuenta del proveedor de IA no tiene saldo o alcanzó su límite de gasto.",
    ),
    "llm_limite_proveedor": (
        429,
        "El proveedor de IA está limitando las solicitudes de tu clave. Espera un momento.",
    ),
    "llm_proveedor_no_disponible": (
        502,
        "El proveedor de IA no está disponible ahora. Inténtalo de nuevo en unos minutos.",
    ),
    "llm_conexion": (502, "No se pudo conectar con el proveedor de IA. Inténtalo de nuevo."),
    "llm_timeout": (504, "El proveedor de IA tardó demasiado en responder. Inténtalo de nuevo."),
    "llm_rechazo": (
        422,
        "El modelo declinó analizar este documento. Prueba con otro modelo o revísalo a mano.",
    ),
    "llm_respuesta_incompleta": (
        502,
        "El modelo no terminó su respuesta. Inténtalo de nuevo.",
    ),
    "llm_respuesta_invalida": (
        502,
        "El modelo devolvió una respuesta que no se pudo interpretar. Inténtalo de nuevo.",
    ),
    "llm_solicitud_rechazada": (
        502,
        "El proveedor de IA rechazó la solicitud. Prueba con otro modelo.",
    ),
}
_ERROR_GENERICO = (502, "No se pudo completar el análisis con el proveedor de IA.")


def _to_app_error(exc: ProviderError) -> AppError:
    status, mensaje = _ERRORES_LLM.get(exc.code, _ERROR_GENERICO)
    headers = None
    if exc.code == "llm_limite_proveedor":
        headers = {"Retry-After": str(min(exc.retry_after or 30, _RETRY_AFTER_MAX))}
    return AppError(status, exc.code, mensaje, headers=headers)


@dataclass(frozen=True, slots=True)
class _Reserva:
    analisis_id: uuid.UUID
    archivo_key: str
    paginas: int


def resolver_modelo(settings: Settings, proveedor: str, modelo: str | None) -> str:
    info = get_provider(proveedor)
    if info is None or proveedor not in settings.llm_enabled_providers:
        raise invalido(
            "llm_proveedor_no_soportado", "Ese proveedor de IA no está disponible.", "proveedor"
        )
    if modelo is None:
        return info.modelo_predeterminado()
    if not info.permite(modelo):
        raise invalido(
            "llm_modelo_no_permitido", "Ese modelo no está disponible para el análisis.", "modelo"
        )
    return modelo


async def _reservar(
    db: Database,
    settings: Settings,
    principal: Principal,
    descanso_id: uuid.UUID,
    *,
    proveedor: str,
    modelo: str,
) -> _Reserva:
    async with db.session() as session:
        descanso = await get_visible(session, principal, descanso_id)
        if descanso.es_muestra:
            raise prohibido("Las muestras de la demo son de solo lectura.")
        if descanso.estado != PENDIENTE:
            raise conflicto(
                "descanso_no_pendiente", "Solo se puede analizar un descanso que sigue pendiente."
            )
        # Un intento que quedó colgado (caída del servidor) no bloquea al siguiente.
        await session.execute(
            update(AnalisisDescanso)
            .where(
                AnalisisDescanso.descanso_id == descanso.id,
                AnalisisDescanso.estado == "en_proceso",
                AnalisisDescanso.started_at < stale_before(settings),
            )
            .values(estado="fallido", error_code="abandonado", finished_at=datetime.now(UTC))
        )
        realizados = await session.scalar(
            select(func.count())
            .select_from(AnalisisDescanso)
            .where(AnalisisDescanso.descanso_id == descanso.id)
        )
        if (realizados or 0) >= settings.analysis_max_per_descanso:
            raise conflicto(
                "limite_analisis",
                "Este documento ya se analizó el máximo de veces permitido.",
            )
        fila = AnalisisDescanso(
            descanso_id=descanso.id,
            solicitado_por=principal.id,
            proveedor=proveedor,
            modelo=modelo,
            estado="en_proceso",
            version_prompt=PROMPT_VERSION,
            version_reglas=RULES_VERSION,
        )
        session.add(fila)
        try:
            await session.commit()
        except IntegrityError:
            await session.rollback()
            raise conflicto(
                "analisis_en_curso",
                "Ya hay un análisis en curso para este documento. Espera a que termine.",
            ) from None
        return _Reserva(
            analisis_id=fila.id, archivo_key=descanso.archivo_key, paginas=descanso.paginas
        )


async def _marcar_fallido(
    db: Database, reserva: _Reserva, principal: Principal, *, error_code: str, ip: str | None
) -> None:
    async with db.session() as session:
        await session.execute(
            update(AnalisisDescanso)
            .where(AnalisisDescanso.id == reserva.analisis_id)
            .values(estado="fallido", error_code=error_code[:40], finished_at=datetime.now(UTC))
        )
        audit.record(
            session,
            "analisis_fallido",
            actor_id=principal.id,
            entidad="analisis",
            entidad_id=reserva.analisis_id,
            ip=ip,
            detalle={"error_code": error_code},
        )
        await session.commit()


async def _contexto(
    session: AsyncSession,
    settings: Settings,
    principal: Principal,
    descanso: DescansoMedico,
    citt: str | None,
) -> ContextoValidacion:
    colaborador = descanso.colaborador
    hoy = datetime.now(ZoneInfo(settings.tz_negocio)).date()
    # En la demo solo se compara con lo que el propio visitante puede ver: si
    # no, "este documento ya se presentó" revelaría cargas de otros visitantes.
    alcance = visible_filter(principal)

    rangos: list[tuple[date, date]] = [
        (inicio, fin)
        for inicio, fin in (
            await session.execute(
                select(DescansoMedico.fecha_inicio, DescansoMedico.fecha_fin).where(
                    DescansoMedico.colaborador_id == descanso.colaborador_id,
                    DescansoMedico.id != descanso.id,
                    DescansoMedico.estado == "Aprobado",
                    DescansoMedico.fecha_inicio.is_not(None),
                    DescansoMedico.fecha_fin.is_not(None),
                    *alcance,
                )
            )
        ).all()
    ]
    archivo_duplicado = bool(
        await session.scalar(
            select(func.count())
            .select_from(DescansoMedico)
            .where(
                DescansoMedico.archivo_sha256 == descanso.archivo_sha256,
                DescansoMedico.id != descanso.id,
                # Volver a presentar un documento ya rechazado no es un duplicado.
                DescansoMedico.estado != "Rechazado",
                *alcance,
            )
        )
    )
    citt_duplicado = False
    if citt:
        citt_duplicado = bool(
            await session.scalar(
                select(func.count())
                .select_from(AnalisisDescanso)
                .join(DescansoMedico, DescansoMedico.id == AnalisisDescanso.descanso_id)
                .where(
                    AnalisisDescanso.estado == "completado",
                    AnalisisDescanso.descanso_id != descanso.id,
                    AnalisisDescanso.resultado["extraidos"]["citt"].astext == citt,
                    DescansoMedico.estado != "Rechazado",
                    *alcance,
                )
            )
        )
    return ContextoValidacion(
        dni=colaborador.dni,
        nombres=colaborador.nombres,
        apellidos=colaborador.apellidos,
        hoy=hoy,
        rangos_aprobados=tuple(rangos),
        archivo_duplicado=archivo_duplicado,
        citt_duplicado=citt_duplicado,
    )


async def _persistir(
    db: Database,
    settings: Settings,
    principal: Principal,
    descanso_id: uuid.UUID,
    reserva: _Reserva,
    outcome: ExtractionOutcome,
    *,
    duracion_ms: int,
    ip: str | None,
) -> AnalisisDescanso:
    async with db.session() as session:
        # Bloquea el descanso: serializa con una decisión o un borrado simultáneos.
        descanso = await session.scalar(
            select(DescansoMedico)
            .where(DescansoMedico.id == descanso_id)
            .with_for_update(of=DescansoMedico)
        )
        fila = await session.get(AnalisisDescanso, reserva.analisis_id)
        if descanso is None or fila is None:
            # El dueño eliminó el descanso mientras se analizaba.
            raise no_encontrado("El descanso médico ya no existe.")
        citt_leido = (outcome.extraccion.citt or "").strip() or None
        contexto = await _contexto(session, settings, principal, descanso, citt_leido)
        resultado = engine.evaluate(outcome.extraccion, contexto)

        fila.estado = "completado"
        fila.extraccion = outcome.extraccion.model_dump()
        fila.resultado = resultado.to_dict()
        fila.estado_documento = resultado.estado_documento
        fila.modelo_efectivo = (outcome.modelo_efectivo or "")[:80] or None
        fila.tokens_entrada = outcome.tokens_entrada
        fila.tokens_salida = outcome.tokens_salida
        fila.proveedor_request_id = (outcome.request_id or "")[:100] or None
        fila.duracion_ms = duracion_ms
        fila.finished_at = datetime.now(UTC)
        audit.record(
            session,
            "analisis_completado",
            actor_id=principal.id,
            entidad="analisis",
            entidad_id=fila.id,
            ip=ip,
            detalle={
                "proveedor": fila.proveedor,
                "modelo": fila.modelo,
                "estado_documento": resultado.estado_documento,
            },
        )
        await session.commit()
        await session.refresh(fila)
        return fila


async def _llamar_y_persistir(
    db: Database,
    storage: Storage,
    settings: Settings,
    principal: Principal,
    descanso_id: uuid.UUID,
    reserva: _Reserva,
    *,
    proveedor: str,
    modelo: str,
    api_key: SecretStr,
    ip: str | None,
    slots: asyncio.Semaphore,
) -> AnalisisDescanso:
    inicio = time.perf_counter()
    try:
        try:
            paginas = [
                await storage.get(reserva.archivo_key, page_name(n))
                for n in range(1, reserva.paginas + 1)
            ]
        except ObjetoNoEncontrado:
            logger.error("faltan páginas del descanso %s", descanso_id)
            await _marcar_fallido(
                db, reserva, principal, error_code="documento_no_disponible", ip=ip
            )
            raise no_encontrado("El documento ya no está disponible.") from None
        try:
            async with asyncio.timeout(settings.analysis_deadline_seconds):
                outcome = await engine.extract(
                    paginas,
                    provider=proveedor,
                    model=modelo,
                    api_key=api_key,
                    timeout_s=settings.llm_request_timeout_seconds,
                )
        except TimeoutError:
            error: ProviderError = TiempoAgotado("El análisis superó el plazo máximo.")
        except ProviderError as exc:
            error = exc
        else:
            return await _persistir(
                db,
                settings,
                principal,
                descanso_id,
                reserva,
                outcome,
                duracion_ms=int((time.perf_counter() - inicio) * 1000),
                ip=ip,
            )
        # Solo código, estado e id de la petición del proveedor: nunca su cuerpo.
        logger.warning(
            "análisis fallido",
            extra={
                "proveedor": proveedor,
                "modelo": modelo,
                "error_code": error.code,
                "proveedor_status": getattr(error, "status", None),
                "proveedor_request_id": getattr(error, "request_id", None),
            },
        )
        await _marcar_fallido(db, reserva, principal, error_code=error.code, ip=ip)
        raise _to_app_error(error)
    finally:
        slots.release()


async def analizar(
    db: Database,
    storage: Storage,
    settings: Settings,
    principal: Principal,
    descanso_id: uuid.UUID,
    *,
    proveedor: str,
    modelo: str | None,
    api_key: SecretStr,
    ip: str | None,
    slots: asyncio.Semaphore,
    en_vuelo: set[asyncio.Task[AnalisisDescanso]],
) -> AnalisisDescanso:
    modelo_final = resolver_modelo(settings, proveedor, modelo)
    # Tope global de análisis simultáneos: acota memoria y conexiones salientes.
    # No se espera en cola: se responde 503 y el cliente reintenta.
    if slots.locked():
        raise AppError(
            503,
            "servidor_ocupado",
            "Hay muchos análisis en curso. Inténtalo de nuevo en unos segundos.",
            headers={"Retry-After": "10"},
        )
    await slots.acquire()
    try:
        reserva = await _reservar(
            db, settings, principal, descanso_id, proveedor=proveedor, modelo=modelo_final
        )
    except BaseException:
        slots.release()
        raise

    # La llamada ya está pagada por el usuario: si su navegador se desconecta o
    # la petición se cancela, igual termina y se guarda. La tarea libera el cupo.
    tarea = asyncio.create_task(
        _llamar_y_persistir(
            db,
            storage,
            settings,
            principal,
            descanso_id,
            reserva,
            proveedor=proveedor,
            modelo=modelo_final,
            api_key=api_key,
            ip=ip,
            slots=slots,
        ),
        name=f"analisis-{reserva.analisis_id}",
    )
    en_vuelo.add(tarea)
    tarea.add_done_callback(en_vuelo.discard)
    # Si nadie llega a esperar la tarea (petición cancelada), su excepción se
    # consume aquí para que asyncio no la reporte como "nunca recuperada".
    tarea.add_done_callback(lambda t: t.cancelled() or t.exception())
    return await asyncio.shield(tarea)


async def listar(
    db: Database, principal: Principal, descanso_id: uuid.UUID
) -> list[AnalisisDescanso]:
    async with db.session() as session:
        descanso = await get_visible(session, principal, descanso_id)
        filas = await session.scalars(
            select(AnalisisDescanso)
            .where(
                AnalisisDescanso.descanso_id == descanso.id,
                AnalisisDescanso.estado == "completado",
            )
            .order_by(AnalisisDescanso.started_at.desc())
        )
        return list(filas.all())
