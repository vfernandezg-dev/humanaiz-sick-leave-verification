"""Almacenamiento en un directorio local (un volumen privado en producción)."""

from __future__ import annotations

import asyncio
import re
import shutil
import uuid
from datetime import UTC, datetime
from pathlib import Path

from humanaiz.storage.base import ObjetoNoEncontrado

_PREFIX = re.compile(r"^[0-9a-f]{2}/[0-9a-f]{2}/[0-9a-f]{32}$")
_NAME = re.compile(r"^(original|page-[0-9]{1,3}\.jpg)$")


class LocalStorage:
    def __init__(self, root: Path) -> None:
        self.root = root
        root.mkdir(parents=True, exist_ok=True)

    def new_prefix(self) -> str:
        key = uuid.uuid4().hex
        return f"{key[:2]}/{key[2:4]}/{key}"

    def _dir(self, prefix: str) -> Path:
        # Los prefijos los genera el servidor, pero se validan igual: ninguna
        # ruta puede salir del directorio raíz.
        if not _PREFIX.match(prefix):
            raise ValueError("prefijo de almacenamiento no válido")
        return self.root / prefix

    def _file(self, prefix: str, name: str) -> Path:
        if not _NAME.match(name):
            raise ValueError("nombre de objeto no válido")
        return self._dir(prefix) / name

    async def put(self, prefix: str, name: str, data: bytes) -> None:
        path = self._file(prefix, name)

        def write() -> None:
            path.parent.mkdir(parents=True, exist_ok=True)
            temporal = path.with_suffix(path.suffix + ".tmp")
            temporal.write_bytes(data)
            temporal.replace(path)

        await asyncio.to_thread(write)

    async def get(self, prefix: str, name: str) -> bytes:
        path = self._file(prefix, name)
        try:
            return await asyncio.to_thread(path.read_bytes)
        except FileNotFoundError:
            raise ObjetoNoEncontrado(f"{prefix}/{name}") from None

    async def delete_prefix(self, prefix: str) -> None:
        await asyncio.to_thread(shutil.rmtree, self._dir(prefix), True)

    async def list_prefixes(self) -> list[tuple[str, datetime]]:
        def scan() -> list[tuple[str, datetime]]:
            encontrados = []
            for carpeta in self.root.glob("*/*/*"):
                prefix = carpeta.relative_to(self.root).as_posix()
                if carpeta.is_dir() and _PREFIX.match(prefix):
                    modificado = datetime.fromtimestamp(carpeta.stat().st_mtime, tz=UTC)
                    encontrados.append((prefix, modificado))
            return encontrados

        return await asyncio.to_thread(scan)

    async def free_bytes(self) -> int:
        usage = await asyncio.to_thread(shutil.disk_usage, self.root)
        return usage.free
