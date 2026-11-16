from __future__ import annotations

import asyncio
import json
import logging
from datetime import date, timedelta
from pathlib import Path
from typing import Any

import httpx
import pytest
from fastapi import FastAPI
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from humanaiz.models import AnalisisDescanso, AuditLog, Base, DescansoMedico
from humanaiz.scanning import errors
from humanaiz.scanning.providers.fake import FakeAdapter
from humanaiz.scanning.types import Extraccion
from humanaiz.services import demo
from tests import files
from tests.conftest import (
    DEMO_SETTINGS,
    AppFactory,
    SettingsFactory,
    create_user,
    login,
    make_client,
)
from tests.integration.test_descansos import DESCANSOS, subir

CANARIO = "sk-CANARIO-9f8e7d6c5b4a39281706f5e4d3c2b1a0"
CLAVE = {"X-LLM-Api-Key": CANARIO}
HOY = date.today()
INICIO, FIN = HOY - timedelta(days=4), HOY - timedelta(days=2)


def extraccion(**cambios: Any) -> Extraccion:
    base: dict[str, Any] = {
        "es_certificado_medico": True,
        "legible": True,
        "tipo_documento": "citt",
        "dni_en_documento": "45678912",
        "nombre_en_documento": "RAMIREZ SOTO CARLOS DANIEL",
        "citt": "A-123-00045678-26",
        "codigo_medico": "054321",
        "contingencia": "Enfermedad común",
        "fecha_inicio_doc": INICIO.isoformat(),
        "fecha_fin_doc": FIN.isoformat(),
        "fecha_emision_doc": INICIO.isoformat(),
        "dias_documento": 3,
    }
    return Extraccion(**base | cambios)


@pytest.fixture
async def entorno(app_factory: AppFactory, db_session: AsyncSession, fake_provider: FakeAdapter):
    """App con el proveedor simulado, un colaborador con sesión y un analista de RRHH."""
    fake_provider.extraccion = extraccion()
    await create_user(db_session, "45678912", nombres="Carlos Daniel", apellidos="Ramírez Soto")
    await create_user(
        db_session, "33333333", role="analista_rrhh", nombres="Rita", apellidos="Mora"
    )
    async with (
        app_factory(llm_enabled_providers=("fake", "anthropic")) as app,
        make_client(app) as colaborador,
        make_client(app) as rrhh,
    ):
        await login(colaborador, "45678912")
        await login(rrhh, "33333333")
        yield app, colaborador, rrhh, fake_provider


async def analizar(
    client: httpx.AsyncClient, descanso_id: str, cuerpo: dict[str, Any] | None = None, **kw: Any
) -> httpx.Response:
    kw.setdefault("headers", CLAVE)
    return await client.post(
        f"{DESCANSOS}/{descanso_id}/analisis", json=cuerpo or {"proveedor": "fake"}, **kw
    )


async def esperar_tareas(app: FastAPI) -> None:
    pendientes = set(app.state.analisis_en_vuelo)
    if pendientes:
        await asyncio.wait(pendientes, timeout=10)


# ---------- flujo correcto ----------


async def test_analisis_completo_no_modifica_el_descanso(entorno, db_session: AsyncSession) -> None:
    app, colaborador, _, fake = entorno
    d = (
        await subir(colaborador, files.pdf_bytes(2), nombre="c.pdf", tipo="application/pdf")
    ).json()

    r = await analizar(colaborador, d["id"])
    assert r.status_code == 201, r.text
    a = r.json()
    assert a["estado_documento"] == "Aprobado"
    assert a["proveedor"] == "fake" and a["modelo"] == "fake-1"  # modelo por defecto
    assert a["solicitado_por"]["role"] == "colaborador"
    assert a["extraidos"]["dni_en_documento"] == "45678912"
    assert a["extraidos"]["fecha_inicio_doc"] == INICIO.isoformat()
    assert a["validaciones"]["dni_coincide"] is True
    assert {v["codigo"] for v in a["validaciones_detalle"]} >= {"dni_coincide", "fechas_presentes"}
    assert a["motivos_rechazo"] == []
    assert a["uso"] == {"tokens_entrada": 1200, "tokens_salida": 180}
    assert a["version_prompt"] and a["version_reglas"]
    # El proveedor recibió las dos páginas normalizadas y una clave.
    assert fake.llamadas == [{"model": "fake-1", "paginas": 2, "con_clave": True}]

    # El análisis es una sugerencia: ni fechas ni estado del descanso cambian.
    visto = (await colaborador.get(f"{DESCANSOS}/{d['id']}")).json()
    assert visto["estado"] == "Pendiente"
    assert (visto["fecha_inicio"], visto["fecha_fin"]) == (None, None)
    assert visto["ultimo_analisis"]["id"] == a["id"]
    assert visto["analisis_en_curso"] is False

    fila = await db_session.scalar(select(AnalisisDescanso))
    assert fila is not None
    assert (fila.estado, fila.proveedor_request_id) == ("completado", "req_fake_123")
    assert fila.extraccion["citt"] == "A-123-00045678-26"


async def test_rrhh_reanaliza_y_el_historial_va_del_mas_reciente(entorno) -> None:
    _, colaborador, rrhh, fake = entorno
    d = (await subir(colaborador)).json()
    primero = (await analizar(colaborador, d["id"])).json()

    fake.extraccion = extraccion(dni_en_documento="99999999")
    segundo = await analizar(rrhh, d["id"], {"proveedor": "fake", "modelo": "fake-2"})
    assert segundo.status_code == 201
    assert segundo.json()["estado_documento"] == "Rechazado"
    assert segundo.json()["modelo"] == "fake-2"
    assert segundo.json()["solicitado_por"]["role"] == "analista_rrhh"
    assert segundo.json()["motivos_rechazo"] == [
        "El DNI del documento no coincide con el del colaborador."
    ]

    historial = (await rrhh.get(f"{DESCANSOS}/{d['id']}/analisis")).json()
    assert [h["id"] for h in historial] == [segundo.json()["id"], primero["id"]]
    assert (await rrhh.get(f"{DESCANSOS}/{d['id']}")).json()["ultimo_analisis"]["id"] == (
        segundo.json()["id"]
    )


async def test_contexto_duplicados_y_solapamiento(entorno) -> None:
    _, colaborador, rrhh, fake = entorno
    primero = (await subir(colaborador)).json()
    aprobar = {
        "estado": "Aprobado",
        "fecha_inicio": INICIO.isoformat(),
        "fecha_fin": FIN.isoformat(),
    }
    assert (await analizar(colaborador, primero["id"])).json()["estado_documento"] == "Aprobado"
    assert (
        await rrhh.post(f"{DESCANSOS}/{primero['id']}/decision", json=aprobar)
    ).status_code == 200

    # Mismo archivo, mismo CITT y fechas que se cruzan con un descanso ya aprobado.
    segundo = (await subir(colaborador)).json()
    a = (await analizar(colaborador, segundo["id"])).json()
    detalle = {v["codigo"]: v["resultado"] for v in a["validaciones_detalle"]}
    assert detalle["documento_no_duplicado"] == "falla"
    assert detalle["sin_solapamiento"] == "falla"
    assert a["estado_documento"] == "Observado"
    assert a["motivos_rechazo"] == []


# ---------- validación de la petición ----------


@pytest.mark.parametrize(
    "cabeceras",
    [
        {},
        {"X-LLM-Api-Key": ""},
        {"X-LLM-Api-Key": "   "},
        {"X-LLM-Api-Key": "corta"},
        {"X-LLM-Api-Key": "clave con espacios dentro 123456"},
        {"X-LLM-Api-Key": "k" * 600},
    ],
)
async def test_clave_ausente_o_malformada(entorno, cabeceras: dict[str, str]) -> None:
    _, colaborador, _, fake = entorno
    d = (await subir(colaborador)).json()
    r = await analizar(colaborador, d["id"], headers=cabeceras)
    assert (r.status_code, r.json()["error"]["code"]) == (400, "llm_clave_faltante")
    # El error no repite lo recibido y no se llegó a llamar al proveedor.
    for valor in cabeceras.values():
        if valor.strip():
            assert valor not in r.text
    assert fake.llamadas == []


async def test_proveedor_y_modelo_deben_estar_permitidos(entorno) -> None:
    _, colaborador, _, fake = entorno
    d = (await subir(colaborador)).json()
    casos = [
        ({"proveedor": "inventado"}, "llm_proveedor_no_soportado"),
        ({"proveedor": "openai"}, "llm_proveedor_no_soportado"),  # existe pero no está habilitado
        ({"proveedor": "fake", "modelo": "modelo con espacios"}, "llm_modelo_no_permitido"),
        ({"proveedor": "fake", "modelo": "../../v1/keys"}, "llm_modelo_no_permitido"),
        ({"proveedor": "anthropic", "modelo": "fake-1"}, "llm_modelo_no_permitido"),
        ({"modelo": "fake-1"}, "validacion"),
    ]
    for cuerpo, codigo in casos:
        r = await analizar(colaborador, d["id"], cuerpo)
        assert (r.status_code, r.json()["error"]["code"]) == (422, codigo), cuerpo
    assert fake.llamadas == []


async def test_quien_puede_analizar(entorno, db_session: AsyncSession) -> None:
    app, colaborador, rrhh, _ = entorno
    d = (await subir(colaborador)).json()
    await create_user(db_session, "22222222", nombres="Otro", apellidos="Usuario")
    async with make_client(app) as otro:
        await login(otro, "22222222")
        assert (await analizar(otro, d["id"])).status_code == 404
        assert (await otro.get(f"{DESCANSOS}/{d['id']}/analisis")).status_code == 404
    async with make_client(app) as anonimo:
        assert (await analizar(anonimo, d["id"])).status_code == 401

    rechazar = {"estado": "Rechazado", "comentario_rrhh": "Ilegible"}
    assert (await rrhh.post(f"{DESCANSOS}/{d['id']}/decision", json=rechazar)).status_code == 200
    r = await analizar(rrhh, d["id"])
    assert (r.status_code, r.json()["error"]["code"]) == (409, "descanso_no_pendiente")


# ---------- concurrencia ----------


async def test_un_solo_analisis_a_la_vez_por_descanso(entorno) -> None:
    _, colaborador, rrhh, fake = entorno
    d = (await subir(colaborador)).json()
    fake.continuar = asyncio.Event()

    primero = asyncio.create_task(analizar(colaborador, d["id"]))
    await asyncio.wait_for(fake.iniciada.wait(), timeout=5)
    assert (await rrhh.get(f"{DESCANSOS}/{d['id']}")).json()["analisis_en_curso"] is True

    segundo = await analizar(rrhh, d["id"])
    assert (segundo.status_code, segundo.json()["error"]["code"]) == (409, "analisis_en_curso")

    fake.continuar.set()
    assert (await primero).status_code == 201
    assert (await rrhh.get(f"{DESCANSOS}/{d['id']}")).json()["analisis_en_curso"] is False
    assert len(fake.llamadas) == 1


async def test_no_retiene_conexion_de_base_de_datos_mientras_espera_al_proveedor(
    app_factory: AppFactory, db_session: AsyncSession, fake_provider: FakeAdapter
) -> None:
    fake_provider.extraccion = extraccion()
    fake_provider.continuar = asyncio.Event()
    await create_user(db_session, "45678912", nombres="Carlos Daniel", apellidos="Ramírez Soto")
    # Con una sola conexión en el pool: si el análisis la retuviera, todo lo demás se colgaría.
    async with (
        app_factory(llm_enabled_providers=("fake",), db_pool_size=1) as app,
        make_client(app) as cliente,
    ):
        await login(cliente, "45678912")
        d = (await subir(cliente)).json()
        en_curso = asyncio.create_task(analizar(cliente, d["id"]))
        await asyncio.wait_for(fake_provider.iniciada.wait(), timeout=5)

        otra = await asyncio.wait_for(cliente.get("/api/v1/me/descansos"), timeout=5)
        assert otra.status_code == 200
        assert (
            await asyncio.wait_for(cliente.get("/api/v1/auth/me"), timeout=5)
        ).status_code == 200

        fake_provider.continuar.set()
        assert (await en_curso).status_code == 201


async def test_tope_global_de_analisis_simultaneos(
    app_factory: AppFactory, db_session: AsyncSession, fake_provider: FakeAdapter
) -> None:
    fake_provider.extraccion = extraccion()
    fake_provider.continuar = asyncio.Event()
    await create_user(db_session, "45678912", nombres="Carlos Daniel", apellidos="Ramírez Soto")
    async with (
        app_factory(llm_enabled_providers=("fake",), analysis_max_concurrency=1) as app,
        make_client(app) as cliente,
    ):
        await login(cliente, "45678912")
        a = (await subir(cliente)).json()
        b = (await subir(cliente, files.png_bytes(), nombre="b.png", tipo="image/png")).json()
        primero = asyncio.create_task(analizar(cliente, a["id"]))
        await asyncio.wait_for(fake_provider.iniciada.wait(), timeout=5)

        ocupado = await analizar(cliente, b["id"])
        assert (ocupado.status_code, ocupado.json()["error"]["code"]) == (503, "servidor_ocupado")
        assert ocupado.headers["retry-after"] == "10"

        fake_provider.continuar.set()
        assert (await primero).status_code == 201
        # Liberado el cupo, el segundo ya puede analizarse.
        assert (await analizar(cliente, b["id"])).status_code == 201


async def test_si_el_cliente_se_desconecta_el_analisis_igual_se_guarda(
    entorno, db_session: AsyncSession
) -> None:
    app, colaborador, _, fake = entorno
    d = (await subir(colaborador)).json()
    fake.continuar = asyncio.Event()

    peticion = asyncio.create_task(analizar(colaborador, d["id"]))
    await asyncio.wait_for(fake.iniciada.wait(), timeout=5)
    peticion.cancel()  # el navegador cierra la conexión a mitad del análisis
    with pytest.raises(asyncio.CancelledError):
        await peticion

    fake.continuar.set()
    await esperar_tareas(app)
    fila = await db_session.scalar(select(AnalisisDescanso))
    assert fila is not None
    assert (fila.estado, fila.estado_documento) == ("completado", "Aprobado")
    # Al volver a consultar, el cliente encuentra el resultado.
    assert (await colaborador.get(f"{DESCANSOS}/{d['id']}")).json()["ultimo_analisis"] is not None


async def test_borrar_el_descanso_durante_el_analisis(entorno, db_session: AsyncSession) -> None:
    _, colaborador, _, fake = entorno
    d = (await subir(colaborador)).json()
    fake.continuar = asyncio.Event()
    peticion = asyncio.create_task(analizar(colaborador, d["id"]))
    await asyncio.wait_for(fake.iniciada.wait(), timeout=5)

    assert (await colaborador.delete(f"{DESCANSOS}/{d['id']}")).status_code == 204
    fake.continuar.set()
    r = await peticion
    assert (r.status_code, r.json()["error"]["code"]) == (404, "no_encontrado")
    assert await db_session.scalar(select(AnalisisDescanso)) is None


# ---------- errores del proveedor ----------


@pytest.mark.parametrize(
    ("error", "estado", "codigo"),
    [
        (errors.ClaveInvalida("x"), 400, "llm_clave_invalida"),
        (errors.SinAccesoModelo("x"), 400, "llm_sin_acceso_modelo"),
        (errors.SinSaldo("x"), 402, "llm_sin_saldo"),
        (errors.LimiteProveedor("x", retry_after=500), 429, "llm_limite_proveedor"),
        (errors.ProveedorNoDisponible("x"), 502, "llm_proveedor_no_disponible"),
        (errors.ErrorConexion("x"), 502, "llm_conexion"),
        (errors.TiempoAgotado("x"), 504, "llm_timeout"),
        (errors.Rechazo("x"), 422, "llm_rechazo"),
        (errors.RespuestaIncompleta("x"), 502, "llm_respuesta_incompleta"),
        (errors.RespuestaInvalida("x"), 502, "llm_respuesta_invalida"),
        (errors.SolicitudRechazada("x"), 502, "llm_solicitud_rechazada"),
        (RuntimeError(f"algo inesperado con {CANARIO}"), 502, "llm_proveedor_no_disponible"),
    ],
)
async def test_errores_del_proveedor_llegan_con_codigo_propio(
    entorno, db_session: AsyncSession, error: Exception, estado: int, codigo: str
) -> None:
    _, colaborador, _, fake = entorno
    d = (await subir(colaborador)).json()
    fake.error = error

    r = await analizar(colaborador, d["id"])
    assert (r.status_code, r.json()["error"]["code"]) == (estado, codigo)
    # Nunca 401: ese código es solo de la sesión de la aplicación.
    assert r.status_code != 401
    assert CANARIO not in r.text
    if codigo == "llm_limite_proveedor":
        assert r.headers["retry-after"] == "120"  # acotado

    fila = await db_session.scalar(select(AnalisisDescanso))
    assert fila is not None
    assert (fila.estado, fila.error_code, fila.resultado) == ("fallido", codigo, None)
    # Un intento fallido no cuenta como análisis ni bloquea el siguiente.
    assert (await colaborador.get(f"{DESCANSOS}/{d['id']}")).json()["ultimo_analisis"] is None
    assert (await colaborador.get(f"{DESCANSOS}/{d['id']}/analisis")).json() == []
    fake.error = None
    assert (await analizar(colaborador, d["id"])).status_code == 201


async def test_plazo_maximo_del_analisis(
    app_factory: AppFactory, db_session: AsyncSession, fake_provider: FakeAdapter
) -> None:
    fake_provider.extraccion = extraccion()
    fake_provider.continuar = asyncio.Event()  # nunca se activa: el proveedor "no responde"
    await create_user(db_session, "45678912", nombres="Carlos Daniel", apellidos="Ramírez Soto")
    overrides = {"llm_request_timeout_seconds": 1, "analysis_deadline_seconds": 2}
    async with (
        app_factory(llm_enabled_providers=("fake",), **overrides) as app,
        make_client(app) as cliente,
    ):
        await login(cliente, "45678912")
        d = (await subir(cliente)).json()
        r = await asyncio.wait_for(analizar(cliente, d["id"]), timeout=10)
        assert (r.status_code, r.json()["error"]["code"]) == (504, "llm_timeout"), r.text
        fila = await db_session.scalar(select(AnalisisDescanso))
        assert fila is not None
        assert (fila.estado, fila.error_code) == ("fallido", "llm_timeout")


async def test_limites_de_uso_del_analisis(
    app_factory: AppFactory, db_session: AsyncSession, fake_provider: FakeAdapter
) -> None:
    fake_provider.extraccion = extraccion()
    await create_user(db_session, "45678912", nombres="Carlos Daniel", apellidos="Ramírez Soto")
    async with (
        app_factory(llm_enabled_providers=("fake",), analysis_max_per_descanso=2) as app,
        make_client(app) as cliente,
    ):
        await login(cliente, "45678912")
        d = (await subir(cliente)).json()
        codigos = [(await analizar(cliente, d["id"])).status_code for _ in range(3)]
        assert codigos == [201, 201, 409]
        ultimo = await analizar(cliente, d["id"])
        assert ultimo.json()["error"]["code"] == "limite_analisis"

    async with (
        app_factory(llm_enabled_providers=("fake",), rate_limit_analysis="1/hour") as app,
        make_client(app) as cliente,
    ):
        await login(cliente, "45678912")
        otro = (await subir(cliente, files.png_bytes(), nombre="o.png", tipo="image/png")).json()
        assert (await analizar(cliente, otro["id"])).status_code == 201
        frenado = await analizar(cliente, otro["id"])
        assert (frenado.status_code, frenado.json()["error"]["code"]) == (429, "rate_limit")


# ---------- demo ----------


async def test_demo_el_analisis_respeta_el_aislamiento_por_visitante(
    app_factory: AppFactory,
    make_settings: SettingsFactory,
    db_session: AsyncSession,
    fake_provider: FakeAdapter,
) -> None:
    fake_provider.extraccion = extraccion(dni_en_documento="10000001")
    overrides = DEMO_SETTINGS | {"llm_enabled_providers": ("fake",)}
    await demo.seed(db_session, make_settings(**overrides))
    async with app_factory(**overrides) as app, make_client(app) as v1, make_client(app) as v2:
        await login(v1, "10000001", "demo-colaborador")
        await login(v2, "10000002", "demo-rrhh")
        d = (await subir(v1)).json()

        assert (await analizar(v2, d["id"])).status_code == 404  # RRHH de otro visitante
        assert (await analizar(v1, d["id"])).status_code == 201

        # El mismo archivo subido por otro visitante no delata que "ya se presentó".
        await v2.post("/api/v1/auth/logout")
        await login(v2, "10000001", "demo-colaborador")
        ajeno = (await subir(v2)).json()
        a = (await analizar(v2, ajeno["id"])).json()
        detalle = {v["codigo"]: v["resultado"] for v in a["validaciones_detalle"]}
        assert detalle["documento_no_duplicado"] == "ok"


# ---------- la clave no se guarda en ningún sitio ----------


async def test_canario_la_clave_no_queda_en_base_de_datos_logs_ni_archivos(
    entorno, db_session: AsyncSession, caplog: pytest.LogCaptureFixture
) -> None:
    app, colaborador, rrhh, fake = entorno
    d = (await subir(colaborador)).json()
    respuestas: list[httpx.Response] = []
    with caplog.at_level(logging.DEBUG):
        respuestas.append(await analizar(colaborador, d["id"]))  # correcto
        fake.error = errors.ClaveInvalida("rechazada")
        respuestas.append(await analizar(rrhh, d["id"]))  # el proveedor rechaza la clave
        fake.error = RuntimeError(f"traza con la clave {CANARIO}")
        respuestas.append(await analizar(rrhh, d["id"]))  # fallo inesperado
        fake.error = None
        respuestas.append(await analizar(colaborador, d["id"], headers={"X-LLM-Api-Key": "x"}))
        respuestas.append(await colaborador.get(f"{DESCANSOS}/{d['id']}"))
        respuestas.append(await colaborador.get(f"{DESCANSOS}/{d['id']}/analisis"))
    assert [r.status_code for r in respuestas] == [201, 400, 502, 400, 200, 200]

    # 1. Respuestas HTTP (cuerpo y cabeceras).
    for r in respuestas:
        assert CANARIO not in r.text
        assert CANARIO not in json.dumps(dict(r.headers))
    # 2. Logs de la aplicación, a nivel DEBUG.
    assert CANARIO not in caplog.text
    # 3. Todas las tablas de la base de datos, volcadas como texto.
    for tabla in Base.metadata.sorted_tables:
        filas = (
            await db_session.execute(text(f'SELECT row_to_json(t)::text FROM "{tabla.name}" t'))
        ).scalars()
        for fila in filas:
            assert CANARIO not in fila, tabla.name
    # 4. Todos los archivos del almacenamiento.
    raiz: Path = app.state.settings.storage_local_path
    for archivo in raiz.rglob("*"):
        if archivo.is_file():
            assert CANARIO.encode() not in archivo.read_bytes()
    # Y sí quedó registro de lo ocurrido, sin la clave.
    acciones = set(await db_session.scalars(select(AuditLog.accion)))
    assert {"analisis_completado", "analisis_fallido"} <= acciones
    assert await db_session.scalar(select(DescansoMedico.id)) is not None
