"""Elige el almacenamiento según STORAGE_BACKEND."""

from __future__ import annotations

from humanaiz.config import Settings
from humanaiz.db import Database
from humanaiz.storage.base import Storage
from humanaiz.storage.database import DatabaseStorage
from humanaiz.storage.local import LocalStorage


def crear_storage(settings: Settings, db: Database) -> Storage:
    if settings.storage_backend == "database":
        return DatabaseStorage(db)
    return LocalStorage(settings.storage_local_path)
