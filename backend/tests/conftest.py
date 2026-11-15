"""Fixtures comunes. Los tests de integración usan un PostgreSQL real.

Levántalo con `docker compose -f docker-compose.dev.yml up -d --wait` o apunta
TEST_DATABASE_URL a otra base vacía (se borra y recrea en cada sesión).
"""

from __future__ import annotations

import os
from collections.abc import AsyncIterator, Callable
from contextlib import AbstractAsyncContextManager, asynccontextmanager
from datetime import date
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
from humanaiz.models import Base, Colaborador, User
from humanaiz.security.passwords import hash_password

TEST_DATABASE_URL = os.environ.get(
    "TEST_DATABASE_URL",
    "postgresql+asyncpg://humanaiz:humanaiz@127.0.0.1:54329/humanaiz_test",
)
ORIGIN = "https://humanaiz.test"
PASSWORD = "contraseña-de-prueba"

SettingsFactory = Callable[..., Settings]
AppFactory = Callable[..., AbstractAsyncContextManager[FastAPI]]

DEMO_SETTINGS: dict[str, Any] = {
    "demo_mode": True,
    "demo_colaborador_dni": "10000001",
    "demo_colaborador_password": "demo-colaborador",
    "demo_rrhh_dni": "10000002",
    "demo_rrhh_password": "demo-rrhh",
}

# Un solo hash para toda la suite: Argon2 es lento a propósito.
_PASSWORD_HASH = hash_password(PASSWORD)


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
            "purge_interval_seconds": 0,
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
def app_factory(make_settings: SettingsFactory, clean_db: None) -> AppFactory:
    @asynccontextmanager
    async def factory(**overrides: Any) -> AsyncIterator[FastAPI]:
        app = create_app(make_settings(**overrides))
        async with app.router.lifespan_context(app):
            yield app

    return factory


@pytest.fixture
async def app(app_factory: AppFactory) -> AsyncIterator[FastAPI]:
    async with app_factory() as app:
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


async def create_user(
    session: AsyncSession,
    dni: str,
    *,
    role: str = "colaborador",
    is_demo: bool = False,
    is_active: bool = True,
    con_colaborador: bool = True,
    nombres: str = "Ana María",
    apellidos: str = "Pérez Gómez",
) -> User:
    user = User(
        dni=dni,
        nombres=nombres,
        apellidos=apellidos,
        role=role,
        is_demo=is_demo,
        is_active=is_active,
        password_hash=_PASSWORD_HASH,
    )
    session.add(user)
    if con_colaborador:
        session.add(
            Colaborador(
                dni=dni,
                user=user,
                nombres=nombres,
                apellidos=apellidos,
                fecha_nacimiento=date(1990, 1, 15),
                categoria="B",
                sexo="F",
                area_operacion="Operaciones",
                tipo_contrato="Indeterminado",
                sede="Lima Centro",
            )
        )
    await session.commit()
    return user


async def login(client: httpx.AsyncClient, dni: str, password: str = PASSWORD) -> dict[str, Any]:
    """Inicia sesión y deja el token de acceso como cabecera por defecto del cliente."""
    r = await client.post("/api/v1/auth/login", json={"dni": dni, "password": password})
    assert r.status_code == 200, r.text
    body = r.json()
    client.headers["Authorization"] = f"Bearer {body['access_token']}"
    return body
