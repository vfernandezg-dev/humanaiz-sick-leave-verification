"""Token de acceso (JWT de vida corta) y token de sesión (opaco, en cookie)."""

from __future__ import annotations

import hashlib
import secrets
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

import jwt

from humanaiz.config import Settings
from humanaiz.errors import AppError, no_autenticado

_ALGORITHM = "HS256"
_AUDIENCE = "humanaiz-api"


@dataclass(frozen=True, slots=True)
class AccessClaims:
    user_id: uuid.UUID
    session_id: uuid.UUID
    visitor_id: uuid.UUID | None


def create_access_token(
    settings: Settings,
    *,
    user_id: uuid.UUID,
    session_id: uuid.UUID,
    visitor_id: uuid.UUID | None,
) -> str:
    now = datetime.now(UTC)
    payload = {
        "sub": str(user_id),
        "sid": str(session_id),
        "aud": _AUDIENCE,
        "iat": now,
        "exp": now + timedelta(seconds=settings.access_token_ttl_seconds),
    }
    if visitor_id is not None:
        payload["vid"] = str(visitor_id)
    return jwt.encode(payload, settings.jwt_secret.get_secret_value(), algorithm=_ALGORITHM)


def decode_access_token(settings: Settings, token: str) -> AccessClaims:
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret.get_secret_value(),
            algorithms=[_ALGORITHM],
            audience=_AUDIENCE,
            options={"require": ["sub", "sid", "exp", "iat", "aud"]},
        )
        return AccessClaims(
            user_id=uuid.UUID(payload["sub"]),
            session_id=uuid.UUID(payload["sid"]),
            visitor_id=uuid.UUID(payload["vid"]) if payload.get("vid") else None,
        )
    except jwt.ExpiredSignatureError:
        raise _expirado() from None
    except (jwt.InvalidTokenError, ValueError, KeyError):
        raise no_autenticado() from None


def _expirado() -> AppError:
    return no_autenticado("token_expirado", "Tu sesión necesita renovarse.")


def new_session_token() -> tuple[str, bytes]:
    """Devuelve (token para la cookie, hash que se guarda en la base de datos)."""
    raw = secrets.token_urlsafe(32)
    return raw, hash_session_token(raw)


def hash_session_token(raw: str) -> bytes:
    # El token ya tiene 256 bits de entropía: basta un SHA-256, sin sal ni KDF.
    return hashlib.sha256(raw.encode()).digest()
