"""Inicio, renovación y cierre de sesión."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from humanaiz.config import Settings
from humanaiz.errors import AppError, no_autenticado
from humanaiz.models import User, UserSession
from humanaiz.security.passwords import verify_password
from humanaiz.security.tokens import create_access_token, hash_session_token, new_session_token
from humanaiz.services import audit


@dataclass(frozen=True, slots=True)
class SesionIniciada:
    user: User
    session_id: uuid.UUID
    visitor_id: uuid.UUID | None
    access_token: str
    session_token: str | None  # solo al iniciar sesión: va a la cookie
    session_max_age: int


def _credenciales_invalidas() -> AppError:
    # Mismo mensaje para DNI inexistente, contraseña errónea o cuenta inactiva.
    return AppError(401, "credenciales_invalidas", "DNI o contraseña incorrectos.")


def _sesion_invalida() -> AppError:
    return no_autenticado("sesion_invalida", "Tu sesión terminó. Inicia sesión de nuevo.")


def parse_visitor_cookie(value: str | None) -> uuid.UUID | None:
    if not value:
        return None
    try:
        return uuid.UUID(value)
    except ValueError:
        return None


async def login(
    session: AsyncSession,
    settings: Settings,
    *,
    dni: str,
    password: str,
    terminos_version: str,
    ip: str | None,
    user_agent: str | None,
    visitor_cookie: str | None,
) -> SesionIniciada:
    user = await session.scalar(
        select(User).options(selectinload(User.colaborador)).where(User.dni == dni)
    )
    password_ok = await verify_password(user.password_hash if user else None, password)
    if user is None or not password_ok or not user.is_active:
        audit.record(session, "login_fallido", ip=ip, detalle={"dni": dni})
        await session.commit()
        raise _credenciales_invalidas()

    visitor_id: uuid.UUID | None = None
    if user.is_demo:
        # El identificador de visitante sobrevive al cierre de sesión: así un
        # mismo navegador puede subir como colaborador y revisar como RRHH.
        visitor_id = parse_visitor_cookie(visitor_cookie) or uuid.uuid4()

    ttl = (
        settings.demo_session_ttl_seconds if user.is_demo else settings.session_absolute_ttl_seconds
    )
    raw_token, token_hash = new_session_token()
    now = datetime.now(UTC)
    row = UserSession(
        user_id=user.id,
        token_hash=token_hash,
        visitor_id=visitor_id,
        expires_at=now + timedelta(seconds=ttl),
        ip=ip,
        user_agent=(user_agent or "")[:200] or None,
    )
    session.add(row)
    await session.flush()
    # Queda constancia de qué versión de los términos aceptó en este inicio de sesión.
    audit.record(
        session, "login", actor_id=user.id, ip=ip, detalle={"terminos_version": terminos_version}
    )
    await session.commit()

    return SesionIniciada(
        user=user,
        session_id=row.id,
        visitor_id=visitor_id,
        access_token=create_access_token(
            settings, user_id=user.id, session_id=row.id, visitor_id=visitor_id
        ),
        session_token=raw_token,
        session_max_age=ttl,
    )


async def refresh(
    session: AsyncSession, settings: Settings, *, session_token: str | None
) -> SesionIniciada:
    if not session_token:
        raise _sesion_invalida()
    now = datetime.now(UTC)
    row = await session.scalar(
        select(UserSession)
        .options(selectinload(UserSession.user).selectinload(User.colaborador))
        .where(UserSession.token_hash == hash_session_token(session_token))
    )
    if (
        row is None
        or row.revoked_at is not None
        or row.expires_at <= now
        or now - row.last_used_at > timedelta(seconds=settings.session_idle_ttl_seconds)
        or not row.user.is_active
    ):
        raise _sesion_invalida()

    row.last_used_at = now
    await session.commit()
    return SesionIniciada(
        user=row.user,
        session_id=row.id,
        visitor_id=row.visitor_id,
        access_token=create_access_token(
            settings, user_id=row.user_id, session_id=row.id, visitor_id=row.visitor_id
        ),
        session_token=None,
        session_max_age=max(0, int((row.expires_at - now).total_seconds())),
    )


async def logout(session: AsyncSession, *, session_token: str | None, ip: str | None) -> None:
    """Revoca solo la sesión de esta cookie. Idempotente."""
    if not session_token:
        return
    result = await session.execute(
        update(UserSession)
        .where(
            UserSession.token_hash == hash_session_token(session_token),
            UserSession.revoked_at.is_(None),
        )
        .values(revoked_at=datetime.now(UTC))
        .returning(UserSession.user_id)
    )
    user_id = result.scalar_one_or_none()
    if user_id is not None:
        audit.record(session, "logout", actor_id=user_id, ip=ip)
    await session.commit()
