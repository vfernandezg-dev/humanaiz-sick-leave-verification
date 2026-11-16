"""Almacenamiento en la propia base de datos (tabla `archivos_guardados`).

Para plataformas sin disco persistente, como Vercel: las imágenes viven junto a
los descansos en PostgreSQL. Es razonable porque cada una es una re-codificación
acotada (máx. 2400 px, unos cientos de KB), su total tiene tope (STORAGE_MAX_MB)
y en la demo caducan a las 24 horas. Para volúmenes reales conviene un
almacenamiento de objetos (S3, R2) detrás del mismo protocolo.
"""

from __future__ import annotations

import re
import uuid
from datetime import datetime

from sqlalchemy import delete, func, select
from sqlalchemy.dialects.postgresql import insert

from humanaiz.db import Database
from humanaiz.models import ArchivoGuardado
from humanaiz.storage.base import ObjetoNoEncontrado

_PREFIX = re.compile(r"^[0-9a-f]{2}/[0-9a-f]{2}/[0-9a-f]{32}$")
_NAME = re.compile(r"^page-[0-9]{1,3}\.jpg$")
# Sin disco que se llene: el límite es STORAGE_MAX_MB, que se comprueba aparte.
_SIN_LIMITE_DE_DISCO = 1 << 62


def _validar(prefix: str, name: str | None = None) -> None:
    if not _PREFIX.match(prefix):
        raise ValueError("prefijo de almacenamiento no válido")
    if name is not None and not _NAME.match(name):
        raise ValueError("nombre de objeto no válido")


class DatabaseStorage:
    def __init__(self, db: Database) -> None:
        self.db = db

    def new_prefix(self) -> str:
        key = uuid.uuid4().hex
        return f"{key[:2]}/{key[2:4]}/{key}"

    async def put(self, prefix: str, name: str, data: bytes) -> None:
        _validar(prefix, name)
        sentencia = insert(ArchivoGuardado).values(prefijo=prefix, nombre=name, datos=data)
        async with self.db.session() as session:
            await session.execute(
                sentencia.on_conflict_do_update(
                    index_elements=["prefijo", "nombre"], set_={"datos": sentencia.excluded.datos}
                )
            )
            await session.commit()

    async def get(self, prefix: str, name: str) -> bytes:
        _validar(prefix, name)
        async with self.db.session() as session:
            datos = await session.scalar(
                select(ArchivoGuardado.datos).where(
                    ArchivoGuardado.prefijo == prefix, ArchivoGuardado.nombre == name
                )
            )
        if datos is None:
            raise ObjetoNoEncontrado(f"{prefix}/{name}")
        return datos

    async def delete_prefix(self, prefix: str) -> None:
        _validar(prefix)
        async with self.db.session() as session:
            await session.execute(delete(ArchivoGuardado).where(ArchivoGuardado.prefijo == prefix))
            await session.commit()

    async def list_prefixes(self) -> list[tuple[str, datetime]]:
        async with self.db.session() as session:
            filas = await session.execute(
                select(ArchivoGuardado.prefijo, func.max(ArchivoGuardado.created_at)).group_by(
                    ArchivoGuardado.prefijo
                )
            )
            return [(prefijo, creado) for prefijo, creado in filas.all()]

    async def free_bytes(self) -> int:
        return _SIN_LIMITE_DE_DISCO
