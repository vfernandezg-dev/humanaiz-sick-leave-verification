"""Fixtures comunes. Los tests de integración usan un PostgreSQL real.

Levántalo con `docker compose -f docker-compose.dev.yml up -d --wait` o apunta
TEST_DATABASE_URL a otra base vacía (se borra y recrea en cada sesión).
"""

from __future__ import annotations

import os
from collections.abc import AsyncIterator, Callable
from pathlib import Path
from typing import Any

import httpx
import pytest
from fastapi import FastAPI
from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from humanaiz.config import Settings
from humanaiz.main import create_app
from humanaiz.models import Base

TEST_DATABASE_URL = os.environ.get(
    "TEST_DATABASE_URL",
    "postgresql+asyncpg://humanaiz:humanaiz@127.0.0.1:54329/humanaiz_test",
)
ORIGIN = "https://humanaiz.test"

SettingsFactory = Callable[..., Settings]


@pytest.fixture
def make_settings(tmp_path: Path) -> SettingsFactory:
    def factory(**overrides: Any) -> Settings:
        values: dict[str, Any] = {
            "environment": "test",
            "public_origin": ORIGIN,
            "database_url": TEST_DATABASE_URL,
            "db_pool_size": 5,
            "jwt_secret": "s" * 48,
            "cookie_secure": True,
            "storage_local_path": tmp_path / "uploads",
            "min_free_disk_mb": 0,
            "rate_limit_login": "1000/minute",
            "rate_limit_upload": "1000/minute",
            "rate_limit_analysis": "1000/minute",
            "rate_limit_general": "10000/minute",
        }
        values.update(overrides)
        return Settings(**values)

    return factory


@pytest.fixture(scope="session")
async def engine() -> AsyncIterator[AsyncEngine]:
    engine = create_async_engine(TEST_DATABASE_URL)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest.fixture
async def clean_db(engine: AsyncEngine) -> None:
    tables = ", ".join(f'"{t.name}"' for t in Base.metadata.sorted_tables)
    async with engine.begin() as conn:
        await conn.execute(text(f"TRUNCATE {tables} RESTART IDENTITY CASCADE"))


@pytest.fixture
async def db_session(engine: AsyncEngine, clean_db: None) -> AsyncIterator[AsyncSession]:
    async with async_sessionmaker(engine, expire_on_commit=False)() as session:
        yield session


@pytest.fixture
async def app(make_settings: SettingsFactory, clean_db: None) -> AsyncIterator[FastAPI]:
    app = create_app(make_settings())
    async with app.router.lifespan_context(app):
        yield app


def make_client(app: FastAPI, *, ip: str = "203.0.113.10") -> httpx.AsyncClient:
    """Cliente HTTP contra la app en proceso, con el Origin del sitio por defecto."""
    return httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app, client=(ip, 51000)),
        base_url=ORIGIN,
        headers={"Origin": ORIGIN},
    )


@pytest.fixture
async def client(app: FastAPI) -> AsyncIterator[httpx.AsyncClient]:
    async with make_client(app) as client:
        yield client
