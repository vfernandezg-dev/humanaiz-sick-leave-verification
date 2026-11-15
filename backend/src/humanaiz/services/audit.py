"""Bitácora de auditoría. Se escribe en la misma transacción que la acción."""

from __future__ import annotations

import ipaddress
import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from humanaiz.models import AuditLog

# Solo estas claves pueden ir en `detalle`: evita que algún día se cuele un
# dato sensible (una clave, el contenido de un documento) en la bitácora.
_DETALLE_PERMITIDO = frozenset(
    {
        "dni",
        "motivo",
        "estado",
        "estado_anterior",
        "proveedor",
        "modelo",
        "error_code",
        "estado_documento",
        "paginas",
        "mime",
        "cantidad",
        "pagina",
    }
)


def _ip_valida(ip: str | None) -> str | None:
    if not ip:
        return None
    try:
        return str(ipaddress.ip_address(ip))
    except ValueError:
        return None


def record(
    session: AsyncSession,
    accion: str,
    *,
    actor_id: uuid.UUID | None = None,
    entidad: str | None = None,
    entidad_id: uuid.UUID | None = None,
    ip: str | None = None,
    detalle: dict[str, Any] | None = None,
) -> None:
    if detalle:
        extra = set(detalle) - _DETALLE_PERMITIDO
        if extra:
            raise ValueError(f"Claves no permitidas en la bitácora: {sorted(extra)}")
    session.add(
        AuditLog(
            actor_id=actor_id,
            accion=accion,
            entidad=entidad,
            entidad_id=entidad_id,
            ip=_ip_valida(ip),
            detalle=detalle or None,
        )
    )
