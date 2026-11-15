"""Interfaz de almacenamiento de documentos.

Cada documento ocupa un prefijo generado por el servidor (nunca derivado del
nombre de archivo del usuario) y contiene `original` y `page-N.jpg`. Hoy hay una
implementación en disco local; una compatible con S3 solo tiene que cumplir
este protocolo.
"""

from __future__ import annotations

from datetime import datetime
from typing import Protocol

ORIGINAL = "original"


def page_name(numero: int) -> str:
    return f"page-{numero}.jpg"


class ObjetoNoEncontrado(Exception):
    pass


class Storage(Protocol):
    def new_prefix(self) -> str:
        """Prefijo nuevo y único para un documento."""
        ...

    async def put(self, prefix: str, name: str, data: bytes) -> None: ...

    async def get(self, prefix: str, name: str) -> bytes:
        """Lanza `ObjetoNoEncontrado` si no existe."""
        ...

    async def delete_prefix(self, prefix: str) -> None:
        """Borra el documento completo. No falla si ya no existe."""
        ...

    async def list_prefixes(self) -> list[tuple[str, datetime]]:
        """Todos los prefijos con su fecha de modificación (para barrer huérfanos)."""
        ...

    async def free_bytes(self) -> int: ...
