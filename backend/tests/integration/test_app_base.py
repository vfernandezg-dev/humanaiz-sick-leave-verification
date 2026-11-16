from __future__ import annotations

import httpx
from fastapi import FastAPI

from tests.conftest import ORIGIN


async def test_live_incluye_cabeceras_base(client: httpx.AsyncClient) -> None:
    r = await client.get("/api/v1/health/live")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}
    assert r.headers["cache-control"] == "no-store"
    assert r.headers["x-content-type-options"] == "nosniff"
    assert len(r.headers["x-request-id"]) == 32


async def test_ready_consulta_la_base(client: httpx.AsyncClient) -> None:
    r = await client.get("/api/v1/health/ready")
    assert r.status_code == 200


async def test_ruta_inexistente_usa_el_sobre_de_error(client: httpx.AsyncClient) -> None:
    r = await client.get("/api/v1/no-existe")
    assert r.status_code == 404
    error = r.json()["error"]
    assert error["code"] == "no_encontrado"
    assert error["request_id"] == r.headers["x-request-id"]


async def test_cuerpo_grande_declarado_se_rechaza(client: httpx.AsyncClient) -> None:
    r = await client.post("/api/v1/health/live", content=b"x" * (64 * 1024 + 1))
    assert r.status_code == 413
    assert r.json()["error"]["code"] == "archivo_demasiado_grande"


async def test_cuerpo_grande_sin_content_length_se_rechaza(app: FastAPI) -> None:
    async def trozos():
        for _ in range(80):
            yield b"x" * 1024

    # Con transferencia por trozos no hay Content-Length: el límite se aplica al leer.
    @app.post("/api/v1/_eco")
    async def eco(payload: dict) -> dict:  # pragma: no cover - no debe ejecutarse
        return payload

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url=ORIGIN) as c:
        r = await c.post(
            "/api/v1/_eco", content=trozos(), headers={"content-type": "application/json"}
        )
    assert r.status_code == 413


async def test_error_inesperado_no_filtra_detalles(app: FastAPI) -> None:
    @app.get("/api/v1/_boom")
    async def boom() -> None:
        raise RuntimeError("detalle interno con sk-ant-api03-SECRETO1234567890")

    transport = httpx.ASGITransport(app=app, raise_app_exceptions=False)
    async with httpx.AsyncClient(transport=transport, base_url=ORIGIN) as c:
        r = await c.get("/api/v1/_boom")
    assert r.status_code == 500
    assert r.json()["error"]["code"] == "error_interno"
    assert "SECRETO" not in r.text
    assert "detalle interno" not in r.text
