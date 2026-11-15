"""Dependencias de autenticación y autorización."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from humanaiz.config import Settings
from humanaiz.db import Database
from humanaiz.errors import AppError, no_autenticado, prohibido
from humanaiz.models import User
from humanaiz.security.tokens import decode_access_token

ROLE_RRHH = "analista_rrhh"
ROLE_COLABORADOR = "colaborador"


@dataclass(frozen=True, slots=True)
class Principal:
    """Usuario autenticado de la petición. Objeto plano: no retiene sesión de BD."""

    id: uuid.UUID
    dni: str
    nombres: str
    apellidos: str
    role: str
    is_demo: bool
    session_id: uuid.UUID
    visitor_id: uuid.UUID | None
    colaborador_id: uuid.UUID | None
    colaborador_activo: bool
    colaborador_sede: str | None
    colaborador_area: str | None

    @property
    def es_rrhh(self) -> bool:
        return self.role == ROLE_RRHH

    @property
    def limit_key(self) -> str:
        """Identidad para límites de uso: el visitante en demo, el usuario si no."""
        if self.is_demo and self.visitor_id is not None:
            return f"v:{self.visitor_id}"
        return f"u:{self.id}"


def principal_from_user(
    user: User, *, session_id: uuid.UUID, visitor_id: uuid.UUID | None
) -> Principal:
    colaborador = user.colaborador
    return Principal(
        id=user.id,
        dni=user.dni,
        nombres=user.nombres,
        apellidos=user.apellidos,
        role=user.role,
        is_demo=user.is_demo,
        session_id=session_id,
        visitor_id=visitor_id if user.is_demo else None,
        colaborador_id=colaborador.id if colaborador else None,
        colaborador_activo=bool(colaborador and colaborador.activo),
        colaborador_sede=colaborador.sede if colaborador else None,
        colaborador_area=colaborador.area_operacion if colaborador else None,
    )


def _bearer_token(request: Request) -> str:
    header = request.headers.get("authorization", "")
    scheme, _, token = header.partition(" ")
    if scheme.lower() != "bearer" or not token.strip():
        raise no_autenticado()
    return token.strip()


async def get_principal(request: Request) -> Principal:
    settings: Settings = request.app.state.settings
    db: Database = request.app.state.db
    claims = decode_access_token(settings, _bearer_token(request))
    # Sesión corta y propia: la conexión vuelve al pool antes de ejecutar el
    # endpoint, que puede tardar (p. ej. esperando a un proveedor de IA).
    async with db.session() as session:
        user = await session.scalar(
            select(User).options(selectinload(User.colaborador)).where(User.id == claims.user_id)
        )
        if user is None or not user.is_active:
            raise no_autenticado("sesion_invalida", "Tu sesión ya no es válida. Inicia sesión.")
        principal = principal_from_user(
            user, session_id=claims.session_id, visitor_id=claims.visitor_id
        )
    if principal.is_demo and principal.visitor_id is None:
        # Un usuario demo sin identificador de visitante no tendría aislamiento.
        raise no_autenticado("sesion_invalida", "Tu sesión ya no es válida. Inicia sesión.")
    request.state.principal = principal
    return principal


async def require_rrhh(principal: Annotated[Principal, Depends(get_principal)]) -> Principal:
    if not principal.es_rrhh:
        raise prohibido()
    return principal


def require_same_origin(request: Request) -> None:
    """Defensa CSRF de los endpoints que leen la cookie de sesión.

    SameSite no basta: un subdominio hermano del dominio propio sigue siendo
    "same-site". Se exige que Origin sea exactamente el origen público.
    """
    settings: Settings = request.app.state.settings
    if request.headers.get("origin") != settings.public_origin:
        raise AppError(403, "origen_invalido", "Solicitud rechazada: origen no permitido.")


CurrentUser = Annotated[Principal, Depends(get_principal)]
RRHHUser = Annotated[Principal, Depends(require_rrhh)]
