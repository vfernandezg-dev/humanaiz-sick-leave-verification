"""Hash de contraseñas con Argon2id."""

from __future__ import annotations

import asyncio

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError

_hasher = PasswordHasher()

# Hash de relleno: cuando el DNI no existe se verifica contra él, para que la
# respuesta tarde lo mismo que con un usuario real y no delate qué DNIs existen.
_DUMMY_HASH = _hasher.hash("humanaiz-usuario-inexistente")

# Cada verificación usa ~64 MiB y un núcleo: se acota la concurrencia para que
# una ráfaga de logins no agote la memoria del contenedor.
_MAX_CONCURRENT = 4
_semaphore: asyncio.Semaphore | None = None

PASSWORD_MIN_LENGTH = 10
PASSWORD_MAX_LENGTH = 200


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def validate_new_password(password: str) -> None:
    if not PASSWORD_MIN_LENGTH <= len(password) <= PASSWORD_MAX_LENGTH:
        raise ValueError(
            f"La contraseña debe tener entre {PASSWORD_MIN_LENGTH} y "
            f"{PASSWORD_MAX_LENGTH} caracteres."
        )


def _verify(password_hash: str, password: str) -> bool:
    try:
        return _hasher.verify(password_hash, password)
    except (VerificationError, InvalidHashError):
        return False


async def verify_password(password_hash: str | None, password: str) -> bool:
    """Verifica en un hilo. Con `password_hash=None` gasta el mismo tiempo y devuelve False."""
    global _semaphore
    if _semaphore is None:
        _semaphore = asyncio.Semaphore(_MAX_CONCURRENT)
    async with _semaphore:
        ok = await asyncio.to_thread(_verify, password_hash or _DUMMY_HASH, password)
    return ok and password_hash is not None
