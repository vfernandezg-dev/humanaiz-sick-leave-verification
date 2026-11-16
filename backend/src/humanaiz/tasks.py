"""Mantenimiento periódico: purga de la demo, sesiones caducadas, bitácora antigua y
archivos huérfanos."""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy import delete, or_, select, text, update

from humanaiz.config import Settings
from humanaiz.db import Database
from humanaiz.models import AnalisisDescanso, AuditLog, DescansoMedico, UserSession
from humanaiz.services import audit
from humanaiz.services.descansos import stale_before
from humanaiz.storage.base import Storage

logger = logging.getLogger(__name__)

# Con varias réplicas, el candado consultivo de PostgreSQL deja que solo una
# ejecute la purga en cada ciclo.
_PURGE_LOCK_KEY = 0x48554D41  # "HUMA"
_GRACIA_SESIONES = timedelta(days=1)
_GRACIA_HUERFANOS = timedelta(hours=1)


@dataclass(frozen=True, slots=True)
class ResultadoPurga:
    descansos_demo: int
    sesiones: int
    analisis_abandonados: int
    archivos_huerfanos: int
    registros_auditoria: int = 0

    def hubo_cambios(self) -> bool:
        return any(
            (
                self.descansos_demo,
                self.sesiones,
                self.analisis_abandonados,
                self.archivos_huerfanos,
                self.registros_auditoria,
            )
        )


async def purge_once(db: Database, storage: Storage, settings: Settings) -> ResultadoPurga:
    ahora = datetime.now(UTC)
    async with db.session() as session:
        # Lo que suben los visitantes de la demo caduca; las muestras no.
        prefijos = list(
            (
                await session.execute(
                    delete(DescansoMedico)
                    .where(
                        DescansoMedico.visitor_id.is_not(None),
                        DescansoMedico.es_muestra.is_(False),
                        DescansoMedico.created_at
                        < ahora - timedelta(hours=settings.demo_ttl_hours),
                    )
                    .returning(DescansoMedico.archivo_key)
                )
            )
            .scalars()
            .all()
        )
        sesiones = (
            await session.execute(
                delete(UserSession).where(
                    or_(
                        UserSession.expires_at < ahora - _GRACIA_SESIONES,
                        UserSession.revoked_at < ahora - _GRACIA_SESIONES,
                    )
                )
            )
        ).rowcount
        # Un análisis que quedó "en proceso" (caída del servidor) se cierra
        # para que no bloquee nuevos intentos.
        abandonados = (
            await session.execute(
                update(AnalisisDescanso)
                .where(
                    AnalisisDescanso.estado == "en_proceso",
                    AnalisisDescanso.started_at < stale_before(settings),
                )
                .values(estado="fallido", error_code="abandonado", finished_at=ahora)
            )
        ).rowcount
        # La bitácora guarda IPs: se conserva solo el tiempo indicado en la
        # política de privacidad (AUDIT_RETENTION_DAYS).
        registros = (
            await session.execute(
                delete(AuditLog).where(
                    AuditLog.at < ahora - timedelta(days=settings.audit_retention_days)
                )
            )
        ).rowcount
        if prefijos:
            audit.record(session, "purga_demo", detalle={"cantidad": len(prefijos)})
        await session.commit()

    for prefijo in prefijos:
        await storage.delete_prefix(prefijo)

    # Archivos sin fila en la base (subidas interrumpidas a medio guardar).
    async with db.session() as session:
        conocidos = set(await session.scalars(select(DescansoMedico.archivo_key)))
    huerfanos = 0
    for prefijo, modificado in await storage.list_prefixes():
        if prefijo not in conocidos and ahora - modificado > _GRACIA_HUERFANOS:
            await storage.delete_prefix(prefijo)
            huerfanos += 1

    return ResultadoPurga(
        descansos_demo=len(prefijos),
        sesiones=sesiones or 0,
        analisis_abandonados=abandonados or 0,
        archivos_huerfanos=huerfanos,
        registros_auditoria=registros or 0,
    )


async def purge_loop(db: Database, storage: Storage, settings: Settings) -> None:
    intervalo = settings.purge_interval_seconds
    while True:
        try:
            async with db.engine.connect() as conn:
                if await conn.scalar(
                    text("SELECT pg_try_advisory_lock(:k)"), {"k": _PURGE_LOCK_KEY}
                ):
                    try:
                        resultado = await purge_once(db, storage, settings)
                    finally:
                        await conn.execute(
                            text("SELECT pg_advisory_unlock(:k)"), {"k": _PURGE_LOCK_KEY}
                        )
                    if resultado.hubo_cambios():
                        logger.info(
                            "purga completada",
                            extra={
                                "descansos_demo": resultado.descansos_demo,
                                "sesiones": resultado.sesiones,
                                "analisis_abandonados": resultado.analisis_abandonados,
                                "archivos_huerfanos": resultado.archivos_huerfanos,
                                "registros_auditoria": resultado.registros_auditoria,
                            },
                        )
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("la purga periódica falló; se reintentará")
        await asyncio.sleep(intervalo)
