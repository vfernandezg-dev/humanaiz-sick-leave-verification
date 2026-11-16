from __future__ import annotations

import logging

import httpx
import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from humanaiz.models import Base
from humanaiz.scanning import catalog, errors
from humanaiz.scanning.providers.fake import FakeAdapter
from humanaiz.scanning.types import ModeloDisponible
from tests.conftest import AppFactory, create_user, login, make_client
from tests.integration.test_analisis import CANARIO, CLAVE, analizar, extraccion
from tests.integration.test_descansos import subir

MODELOS = "/api/v1/llm/modelos"


@pytest.fixture
async def cliente(app_factory: AppFactory, db_session: AsyncSession, fake_provider: FakeAdapter):
    await create_user(db_session, "45678912", nombres="Carlos Daniel", apellidos="Ramírez Soto")
    async with (
        app_factory(llm_enabled_providers=("fake", "anthropic", "openrouter")) as app,
        make_client(app) as c,
    ):
        await login(c, "45678912")
        yield c


async def test_lista_modelos_con_los_sugeridos_primero(
    cliente: httpx.AsyncClient, fake_provider: FakeAdapter
) -> None:
    fake_provider.modelos = [
        ModeloDisponible("otro-modelo", "Otro"),
        ModeloDisponible("fake-2", "Simulado 2 (cuenta)"),
        ModeloDisponible("fake-1", "Simulado 1 (cuenta)"),
    ]
    r = await cliente.post(MODELOS, json={"proveedor": "fake"}, headers=CLAVE)
    assert r.status_code == 200, r.text
    cuerpo = r.json()
    assert cuerpo["proveedor"] == "fake"
    assert [(m["id"], m["sugerido"]) for m in cuerpo["modelos"]] == [
        ("fake-1", True),
        ("fake-2", True),
        ("otro-modelo", False),
    ]
    assert cuerpo["modelos"][0]["nombre"] == "Simulado 1 (cuenta)"
    assert fake_provider.llamadas == [{"listar": True, "con_clave": True}]


@pytest.mark.parametrize(
    ("cuerpo", "cabeceras", "estado", "codigo"),
    [
        ({"proveedor": "fake"}, {}, 400, "llm_clave_faltante"),
        ({"proveedor": "inexistente"}, CLAVE, 422, "llm_proveedor_no_soportado"),
        ({"proveedor": "gemini"}, CLAVE, 422, "llm_proveedor_no_soportado"),  # no habilitado
    ],
)
async def test_validacion_de_la_peticion(
    cliente: httpx.AsyncClient, cuerpo: dict, cabeceras: dict, estado: int, codigo: str
) -> None:
    r = await cliente.post(MODELOS, json=cuerpo, headers=cabeceras)
    assert (r.status_code, r.json()["error"]["code"]) == (estado, codigo)


@pytest.mark.parametrize(
    ("error", "estado", "codigo"),
    [
        (errors.ClaveInvalida("x"), 400, "llm_clave_invalida"),
        (errors.SinSaldo("x"), 402, "llm_sin_saldo"),
        (errors.LimiteProveedor("x", retry_after=20), 429, "llm_limite_proveedor"),
        (errors.ErrorConexion("x"), 502, "llm_conexion"),
    ],
)
async def test_errores_del_proveedor(
    cliente: httpx.AsyncClient,
    fake_provider: FakeAdapter,
    error: Exception,
    estado: int,
    codigo: str,
) -> None:
    fake_provider.error = error
    r = await cliente.post(MODELOS, json={"proveedor": "fake"}, headers=CLAVE)
    assert (r.status_code, r.json()["error"]["code"]) == (estado, codigo)
    assert r.status_code != 401  # el 401 es solo de la sesión de la aplicación


async def test_exige_sesion_y_tiene_limite_de_uso(
    app_factory: AppFactory, db_session: AsyncSession, fake_provider: FakeAdapter
) -> None:
    await create_user(db_session, "45678912")
    async with app_factory(llm_enabled_providers=("fake",), rate_limit_modelos="2/hour") as app:
        async with make_client(app) as anonimo:
            r = await anonimo.post(MODELOS, json={"proveedor": "fake"}, headers=CLAVE)
            assert r.status_code == 401
        async with make_client(app) as c:
            await login(c, "45678912")
            estados = [
                (await c.post(MODELOS, json={"proveedor": "fake"}, headers=CLAVE)).status_code
                for _ in range(3)
            ]
    assert estados == [200, 200, 429]


async def test_analisis_con_modelo_libre_y_proveedor_sin_predeterminado(
    cliente: httpx.AsyncClient, fake_provider: FakeAdapter, monkeypatch: pytest.MonkeyPatch
) -> None:
    fake_provider.extraccion = extraccion()
    d = (await subir(cliente)).json()

    # Cualquier modelo con nombre válido, aunque no esté entre los sugeridos.
    libre = await analizar(cliente, d["id"], {"proveedor": "fake", "modelo": "fake-experimental-9"})
    assert libre.status_code == 201, libre.text
    assert fake_provider.llamadas[-1]["model"] == "fake-experimental-9"

    invalido = await analizar(cliente, d["id"], {"proveedor": "fake", "modelo": "../../x"})
    assert (invalido.status_code, invalido.json()["error"]["code"]) == (
        422,
        "llm_modelo_no_permitido",
    )

    # Un proveedor sin modelo predeterminado exige elegir uno.
    sin_defecto = catalog.ProviderInfo(
        id="fake",
        nombre="Simulado",
        familia="openai",
        formato_clave="",
        prefijos_clave=(),
        url_claves="https://example.com",
    )
    monkeypatch.setitem(catalog._BY_ID, "fake", sin_defecto)
    r = await analizar(cliente, d["id"], {"proveedor": "fake"})
    assert (r.status_code, r.json()["error"]["code"]) == (422, "llm_modelo_requerido")


async def test_canario_listar_modelos_no_guarda_la_clave(
    cliente: httpx.AsyncClient,
    fake_provider: FakeAdapter,
    db_session: AsyncSession,
    caplog: pytest.LogCaptureFixture,
) -> None:
    with caplog.at_level(logging.DEBUG):
        ok = await cliente.post(MODELOS, json={"proveedor": "fake"}, headers=CLAVE)
        fake_provider.error = RuntimeError(f"fallo con {CANARIO}")
        fallo = await cliente.post(MODELOS, json={"proveedor": "fake"}, headers=CLAVE)
    assert (ok.status_code, fallo.status_code) == (200, 502)
    for r in (ok, fallo):
        assert CANARIO not in r.text and CANARIO not in str(dict(r.headers))
    assert CANARIO not in caplog.text
    for tabla in Base.metadata.sorted_tables:
        filas = (
            await db_session.execute(text(f'SELECT row_to_json(t)::text FROM "{tabla.name}" t'))
        ).scalars()
        assert all(CANARIO not in fila for fila in filas), tabla.name
