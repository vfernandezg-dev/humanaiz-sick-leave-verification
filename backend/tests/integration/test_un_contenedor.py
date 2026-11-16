"""Despliegue en un solo contenedor (Vercel): imágenes en la base y web servida por la API."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from fastapi import FastAPI
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from humanaiz.config import ConfigError
from humanaiz.models import ArchivoGuardado
from humanaiz.storage.database import DatabaseStorage
from humanaiz.tasks import purge_once
from tests import files
from tests.conftest import AppFactory, create_user, login, make_client

DESCANSOS = "/api/v1/descansos"


def _archivos_en_disco(app: FastAPI) -> list[Path]:
    raiz: Path = app.state.settings.storage_local_path
    return [p for p in raiz.rglob("*") if p.is_file()] if raiz.exists() else []


# ---------- imágenes en la base ----------


async def test_las_imagenes_se_guardan_en_la_base_y_no_en_disco(
    app_factory: AppFactory, db_session: AsyncSession
) -> None:
    await create_user(db_session, "11111111")
    async with app_factory(storage_backend="database") as app, make_client(app) as cliente:
        assert isinstance(app.state.storage, DatabaseStorage)
        await login(cliente, "11111111")
        subida = await cliente.post(
            DESCANSOS,
            data={"sede": "Lima"},
            files={
                "archivo": (
                    "c.jpg",
                    files.jpeg_bytes(orientacion=1) + files.HTML_ADJUNTO,
                    "image/jpeg",
                )
            },
        )
        assert subida.status_code == 201, subida.text
        d = subida.json()

        assert _archivos_en_disco(app) == []
        guardado = await db_session.scalar(select(ArchivoGuardado))
        assert guardado is not None and guardado.nombre == "page-1.jpg"
        assert len(guardado.datos) == d["archivo"]["size_bytes"]
        assert b"<script>" not in guardado.datos and b"FabricanteSecreto" not in guardado.datos

        pagina = await cliente.get(f"{DESCANSOS}/{d['id']}/paginas/1")
        assert pagina.status_code == 200 and pagina.content == guardado.datos
        assert (await cliente.get(f"{DESCANSOS}/{d['id']}/archivo")).content == guardado.datos

        assert (await cliente.delete(f"{DESCANSOS}/{d['id']}")).status_code == 204
        restantes = await db_session.scalar(select(func.count()).select_from(ArchivoGuardado))
        assert restantes == 0


async def test_la_purga_barre_imagenes_huerfanas_en_la_base(
    app_factory: AppFactory, db_session: AsyncSession
) -> None:
    async with app_factory(storage_backend="database") as app:
        storage: DatabaseStorage = app.state.storage
        antiguo, reciente = storage.new_prefix(), storage.new_prefix()
        await storage.put(antiguo, "page-1.jpg", b"x")
        await storage.put(reciente, "page-1.jpg", b"y")
        await storage.put(reciente, "page-1.jpg", b"z")  # sobrescribir no duplica
        await db_session.execute(
            update(ArchivoGuardado)
            .where(ArchivoGuardado.prefijo == antiguo)
            .values(created_at=datetime.now(UTC) - timedelta(hours=3))
        )
        await db_session.commit()

        resultado = await purge_once(app.state.db, storage, app.state.settings)
        assert resultado.archivos_huerfanos == 1
        assert [p for p, _ in await storage.list_prefixes()] == [reciente]
        assert await storage.get(reciente, "page-1.jpg") == b"z"


async def test_el_almacenamiento_en_la_base_valida_prefijos_y_nombres(
    app_factory: AppFactory, db_session: AsyncSession
) -> None:
    async with app_factory(storage_backend="database") as app:
        storage: DatabaseStorage = app.state.storage
        with pytest.raises(ValueError):
            await storage.put("../../otro", "page-1.jpg", b"x")
        with pytest.raises(ValueError):
            await storage.put(storage.new_prefix(), "original", b"x")


# ---------- web servida por la API ----------


@pytest.fixture
def web(tmp_path: Path) -> Path:
    raiz = tmp_path / "web"
    (raiz / "assets").mkdir(parents=True)
    (raiz / "index.html").write_text("<!doctype html><title>HumanAIz</title>", encoding="utf-8")
    (raiz / "assets" / "index-abc123.js").write_text("console.log(1)", encoding="utf-8")
    (tmp_path / "secreto.txt").write_text("no debe salir", encoding="utf-8")
    return raiz


async def test_la_api_sirve_la_web_con_las_cabeceras_de_seguridad(
    app_factory: AppFactory, db_session: AsyncSession, web: Path
) -> None:
    async with app_factory(static_dir=web) as app, make_client(app) as cliente:
        inicio = await cliente.get("/")
        assert inicio.status_code == 200 and "HumanAIz" in inicio.text
        assert inicio.headers["content-type"].startswith("text/html")
        assert "script-src 'self'" in inicio.headers["content-security-policy"]
        assert "connect-src 'self'" in inicio.headers["content-security-policy"]
        assert inicio.headers["strict-transport-security"] == "max-age=31536000"
        assert inicio.headers["x-frame-options"] == "DENY"
        assert inicio.headers["cache-control"] == "no-cache"

        # Las rutas del SPA reciben index.html; los assets, caché inmutable.
        spa = await cliente.get("/descansos/9f1d2c")
        assert spa.status_code == 200 and spa.text == inicio.text
        asset = await cliente.get("/assets/index-abc123.js")
        assert asset.headers["content-type"].startswith("text/javascript")
        assert "immutable" in asset.headers["cache-control"]

        # Un archivo que no existe es 404, no el SPA.
        assert (await cliente.get("/assets/no-existe.js")).status_code == 404
        assert (await cliente.post("/")).status_code == 405


async def test_la_web_no_permite_salir_del_directorio_ni_exponer_rutas_internas(
    app_factory: AppFactory, db_session: AsyncSession, web: Path
) -> None:
    async with app_factory(static_dir=web) as app, make_client(app) as cliente:
        for ruta in ("/../secreto.txt", "/assets/../../secreto.txt", "/%2e%2e/secreto.txt"):
            r = await cliente.get(ruta)
            assert "no debe salir" not in r.text, ruta

        assert (await cliente.get("/api/v1/health/ready")).status_code == 404
        assert (await cliente.get("/api/openapi.json")).status_code == 404

        # La API sigue respondiendo, con las cabeceras comunes.
        vivo = await cliente.get("/api/v1/health/live")
        assert vivo.status_code == 200
        assert vivo.headers["strict-transport-security"] == "max-age=31536000"
        assert "content-security-policy" not in vivo.headers
        assert (
            (await cliente.get("/api/v1/no-existe"))
            .headers["content-type"]
            .startswith("application/json")
        )


async def test_sin_index_html_la_api_no_arranca(app_factory: AppFactory, tmp_path: Path) -> None:
    with pytest.raises(ConfigError, match=r"index\.html"):
        async with app_factory(static_dir=tmp_path):
            pass


def test_el_contrato_no_incluye_las_rutas_de_la_web() -> None:
    """La web no es parte de la API: sus rutas no deben aparecer en el OpenAPI."""
    contrato = Path(__file__).resolve().parents[3] / "frontend" / "openapi.json"
    assert '"/"' not in contrato.read_text(encoding="utf-8")


async def test_un_cliente_http_no_ve_el_disco(
    app_factory: AppFactory, db_session: AsyncSession, web: Path
) -> None:
    # httpx normaliza "..": se prueba también la ruta cruda a nivel ASGI.
    async with app_factory(static_dir=web) as app:
        recibido: list[dict] = []

        async def receive() -> dict:
            return {"type": "http.request", "body": b"", "more_body": False}

        async def send(message: dict) -> None:
            recibido.append(message)

        scope = {
            "type": "http",
            "method": "GET",
            "path": "/../secreto.txt",
            "raw_path": b"/../secreto.txt",
            "query_string": b"",
            "headers": [],
            "client": ("203.0.113.10", 1),
            "server": ("test", 80),
            "scheme": "https",
            "http_version": "1.1",
            "root_path": "",
        }
        await app(scope, receive, send)
        inicio = next(m for m in recibido if m["type"] == "http.response.start")
        cuerpo = b"".join(m.get("body", b"") for m in recibido if m["type"] == "http.response.body")
        assert inicio["status"] == 404
        assert b"no debe salir" not in cuerpo
