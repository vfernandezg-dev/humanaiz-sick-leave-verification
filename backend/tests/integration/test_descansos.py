from __future__ import annotations

import asyncio
import io
from datetime import UTC, datetime, timedelta
from pathlib import Path

import httpx
import pytest
from fastapi import FastAPI
from PIL import Image
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from humanaiz.models import AnalisisDescanso, AuditLog, DescansoMedico, User
from humanaiz.services import demo
from humanaiz.tasks import purge_once
from tests import files
from tests.conftest import (
    DEMO_SETTINGS,
    AppFactory,
    SettingsFactory,
    create_user,
    login,
    make_client,
)

DESCANSOS = "/api/v1/descansos"
MIOS = "/api/v1/me/descansos"


async def subir(
    client: httpx.AsyncClient,
    data: bytes | None = None,
    *,
    sede: str | None = "Lima Centro",
    nombre: str = "certificado.jpg",
    tipo: str = "image/jpeg",
) -> httpx.Response:
    campos = {"sede": sede} if sede is not None else {}
    archivos = {"archivo": (nombre, data if data is not None else files.jpeg_bytes(), tipo)}
    return await client.post(DESCANSOS, data=campos, files=archivos)


def archivos_guardados(app: FastAPI) -> list[Path]:
    raiz: Path = app.state.settings.storage_local_path
    return sorted(p for p in raiz.rglob("*") if p.is_file())


@pytest.fixture
async def colaborador(app: FastAPI, db_session: AsyncSession) -> httpx.AsyncClient:
    await create_user(db_session, "11111111", nombres="Carla", apellidos="Rojas Luna")
    async with make_client(app) as client:
        await login(client, "11111111")
        yield client


@pytest.fixture
async def otro_colaborador(app: FastAPI, db_session: AsyncSession) -> httpx.AsyncClient:
    await create_user(db_session, "22222222", nombres="Diego", apellidos="Salas Vera")
    async with make_client(app) as client:
        await login(client, "22222222")
        yield client


@pytest.fixture
async def rrhh(app: FastAPI, db_session: AsyncSession) -> httpx.AsyncClient:
    await create_user(
        db_session, "33333333", role="analista_rrhh", nombres="Rita", apellidos="Mora Paz"
    )
    async with make_client(app) as client:
        await login(client, "33333333")
        yield client


# ---------- alta ----------


async def test_subir_certificado_crea_descanso_pendiente(
    app: FastAPI, colaborador: httpx.AsyncClient, db_session: AsyncSession
) -> None:
    r = await subir(colaborador, nombre="../../etc/passwd.jpg")
    assert r.status_code == 201, r.text
    d = r.json()
    assert d["estado"] == "Pendiente"
    assert d["sede"] == "Lima Centro"
    assert d["fecha_inicio"] is None and d["fecha_fin"] is None
    assert d["colaborador"]["dni"] == "11111111"
    assert d["archivo"] == {
        "mime": "image/jpeg",
        "size_bytes": len(files.jpeg_bytes()),
        "paginas": 1,
    }
    assert d["ultimo_analisis"] is None and d["analisis_en_curso"] is False
    assert d["es_propio"] is True
    assert d["permisos"] == {
        "puede_analizar": True,
        "puede_decidir": False,
        "puede_eliminar": True,
    }

    # En disco: original + una página, bajo un prefijo generado por el servidor.
    guardados = archivos_guardados(app)
    assert [p.name for p in guardados] == ["original", "page-1.jpg"]
    assert "passwd" not in str(guardados[0])
    fila = await db_session.scalar(select(DescansoMedico))
    assert fila is not None and len(fila.archivo_sha256) == 32
    assert (
        await db_session.scalar(
            select(func.count()).select_from(AuditLog).where(AuditLog.accion == "descanso_creado")
        )
        == 1
    )


async def test_pdf_de_varias_paginas(colaborador: httpx.AsyncClient) -> None:
    r = await subir(colaborador, files.pdf_bytes(3), nombre="cert.pdf", tipo="application/pdf")
    assert r.status_code == 201
    d = r.json()
    assert d["archivo"]["mime"] == "application/pdf"
    assert d["archivo"]["paginas"] == 3
    for numero in (1, 2, 3):
        pagina = await colaborador.get(f"{DESCANSOS}/{d['id']}/paginas/{numero}")
        assert pagina.status_code == 200
        assert pagina.headers["content-type"] == "image/jpeg"
        assert Image.open(io.BytesIO(pagina.content)).format == "JPEG"
    assert (await colaborador.get(f"{DESCANSOS}/{d['id']}/paginas/4")).status_code == 404
    assert (await colaborador.get(f"{DESCANSOS}/{d['id']}/paginas/0")).status_code == 404


async def test_sede_por_defecto_y_validacion(colaborador: httpx.AsyncClient) -> None:
    sin_sede = await subir(colaborador, sede=None)
    assert sin_sede.status_code == 201
    assert sin_sede.json()["sede"] == "Lima Centro"  # la de su ficha

    larga = await subir(colaborador, sede="x" * 101)
    assert larga.status_code == 422
    assert larga.json()["error"]["detalles"][0]["campo"] == "sede"


@pytest.mark.parametrize(
    ("datos", "nombre", "tipo", "estado", "codigo"),
    [
        (files.EJECUTABLE, "certificado.jpg", "image/jpeg", 415, "tipo_no_soportado"),
        (files.HEIC, "foto.heic", "image/heic", 415, "tipo_no_soportado"),
        (b"<html>hola</html>", "cert.pdf", "application/pdf", 415, "tipo_no_soportado"),
        (files.png_bomba(), "cert.png", "image/png", 422, "imagen_demasiado_grande"),
        (files.pdf_cifrado(), "cert.pdf", "application/pdf", 422, "pdf_protegido"),
        (files.pdf_bytes(50), "cert.pdf", "application/pdf", 422, "pdf_demasiadas_paginas"),
        (files.jpeg_bytes()[:300], "cert.jpg", "image/jpeg", 422, "archivo_invalido"),
        (b"", "cert.jpg", "image/jpeg", 422, "archivo_invalido"),
    ],
)
async def test_archivos_rechazados_no_dejan_rastro(
    app: FastAPI,
    colaborador: httpx.AsyncClient,
    db_session: AsyncSession,
    datos: bytes,
    nombre: str,
    tipo: str,
    estado: int,
    codigo: str,
) -> None:
    r = await subir(colaborador, datos, nombre=nombre, tipo=tipo)
    assert (r.status_code, r.json()["error"]["code"]) == (estado, codigo)
    assert archivos_guardados(app) == []
    assert await db_session.scalar(select(func.count()).select_from(DescansoMedico)) == 0


async def test_mensaje_especifico_para_heic(colaborador: httpx.AsyncClient) -> None:
    r = await subir(colaborador, files.HEIC, nombre="foto.heic", tipo="image/heic")
    assert "HEIC" in r.json()["error"]["message"]


async def test_archivo_mayor_al_maximo(app_factory: AppFactory, db_session: AsyncSession) -> None:
    await create_user(db_session, "11111111")
    async with app_factory(max_upload_bytes=200_000) as app, make_client(app) as client:
        await login(client, "11111111")
        # Supera el límite del cuerpo: lo corta el middleware.
        enorme = await subir(client, b"\xff\xd8\xff" + b"0" * 400_000)
        assert enorme.status_code == 413
        # Cabe en el cuerpo (margen del multipart) pero excede el máximo de archivo.
        justo = await subir(client, b"\xff\xd8\xff" + b"0" * 230_000)
        assert justo.status_code == 413
        assert justo.json()["error"]["code"] == "archivo_demasiado_grande"
        assert archivos_guardados(app) == []


async def test_subir_exige_sesion_y_ficha_de_colaborador(
    app: FastAPI, db_session: AsyncSession
) -> None:
    async with make_client(app) as anonimo:
        assert (await subir(anonimo)).status_code == 401
    await create_user(db_session, "44444444", con_colaborador=False)
    async with make_client(app) as sin_ficha:
        await login(sin_ficha, "44444444")
        r = await subir(sin_ficha)
        assert (r.status_code, r.json()["error"]["code"]) == (409, "sin_colaborador_vinculado")
        assert (await sin_ficha.get(MIOS)).json()["total"] == 0


async def test_sin_campo_archivo(colaborador: httpx.AsyncClient) -> None:
    r = await colaborador.post(DESCANSOS, data={"sede": "Lima"})
    assert (r.status_code, r.json()["error"]["code"]) == (422, "archivo_invalido")


async def test_limite_de_subidas(app_factory: AppFactory, db_session: AsyncSession) -> None:
    await create_user(db_session, "11111111")
    async with app_factory(rate_limit_upload="2/hour") as app, make_client(app) as client:
        await login(client, "11111111")
        assert [(await subir(client)).status_code for _ in range(3)] == [201, 201, 429]


async def test_sin_espacio_en_disco(app_factory: AppFactory, db_session: AsyncSession) -> None:
    await create_user(db_session, "11111111")
    async with app_factory(min_free_disk_mb=10**9) as app, make_client(app) as client:
        await login(client, "11111111")
        r = await subir(client)
        assert (r.status_code, r.json()["error"]["code"]) == (503, "almacenamiento_lleno")


# ---------- documentos ----------


async def test_original_se_sirve_solo_como_adjunto(colaborador: httpx.AsyncClient) -> None:
    poliglota = files.jpeg_bytes() + files.HTML_ADJUNTO
    d = (await subir(colaborador, poliglota)).json()

    original = await colaborador.get(f"{DESCANSOS}/{d['id']}/archivo")
    assert original.status_code == 200
    assert original.content == poliglota  # evidencia íntegra
    assert original.headers["content-disposition"].startswith("attachment;")
    assert original.headers["content-type"] == "image/jpeg"
    assert original.headers["x-content-type-options"] == "nosniff"
    assert "sandbox" in original.headers["content-security-policy"]
    assert original.headers["cache-control"] == "no-store"

    # La página que se muestra en pantalla es una re-codificación limpia.
    pagina = await colaborador.get(f"{DESCANSOS}/{d['id']}/paginas/1")
    assert b"<script>" not in pagina.content
    assert "sandbox" in pagina.headers["content-security-policy"]


# ---------- autorización ----------


async def test_un_colaborador_no_ve_lo_de_otro(
    colaborador: httpx.AsyncClient, otro_colaborador: httpx.AsyncClient
) -> None:
    d = (await subir(colaborador)).json()
    base = f"{DESCANSOS}/{d['id']}"

    assert (await otro_colaborador.get(MIOS)).json()["total"] == 0
    for ruta in (base, f"{base}/archivo", f"{base}/paginas/1"):
        r = await otro_colaborador.get(ruta)
        assert (r.status_code, r.json()["error"]["code"]) == (404, "no_encontrado"), ruta
    assert (await otro_colaborador.delete(base)).status_code == 404
    # Decidir y los listados globales son solo de RRHH.
    decision = await otro_colaborador.post(f"{base}/decision", json={"estado": "Aprobado"})
    assert decision.status_code == 403
    assert (await otro_colaborador.get(DESCANSOS)).status_code == 403
    assert (await otro_colaborador.get("/api/v1/colaboradores")).status_code == 403
    assert (await otro_colaborador.get("/api/v1/colaboradores/facetas")).status_code == 403

    mio = (await colaborador.get(MIOS)).json()
    assert mio["total"] == 1 and mio["items"][0]["id"] == d["id"]


async def test_rrhh_ve_todo_y_filtra(
    colaborador: httpx.AsyncClient, otro_colaborador: httpx.AsyncClient, rrhh: httpx.AsyncClient
) -> None:
    a = (await subir(colaborador, sede="Lima Centro")).json()
    b = (await subir(otro_colaborador, sede="Arequipa 100%")).json()

    todos = (await rrhh.get(DESCANSOS)).json()
    assert todos["total"] == 2
    assert {i["id"] for i in todos["items"]} == {a["id"], b["id"]}
    assert all(i["es_propio"] is False for i in todos["items"])
    assert all(i["permisos"]["puede_decidir"] for i in todos["items"])
    assert all(not i["permisos"]["puede_eliminar"] for i in todos["items"])

    por_dni = (await rrhh.get(DESCANSOS, params={"dni": "2222"})).json()
    assert [i["id"] for i in por_dni["items"]] == [b["id"]]
    por_sede = (await rrhh.get(DESCANSOS, params={"sede": "arequipa"})).json()
    assert [i["id"] for i in por_sede["items"]] == [b["id"]]
    # Los comodines de LIKE se tratan como texto.
    assert (await rrhh.get(DESCANSOS, params={"sede": "%"})).json()["total"] == 1
    assert (await rrhh.get(DESCANSOS, params={"sede": "_"})).json()["total"] == 0
    assert (await rrhh.get(DESCANSOS, params={"estado": "Aprobado"})).json()["total"] == 0
    assert (await rrhh.get(DESCANSOS, params={"dni": "12ab"})).status_code == 422

    pagina = (await rrhh.get(DESCANSOS, params={"limit": 1, "offset": 1})).json()
    assert (pagina["total"], len(pagina["items"]), pagina["limit"], pagina["offset"]) == (
        2,
        1,
        1,
        1,
    )

    # RRHH puede ver el documento pero no borrarlo: solo su dueño.
    assert (await rrhh.get(f"{DESCANSOS}/{a['id']}/paginas/1")).status_code == 200
    r = await rrhh.delete(f"{DESCANSOS}/{a['id']}")
    assert (r.status_code, r.json()["error"]["code"]) == (403, "prohibido")


# ---------- decisión ----------


async def test_reglas_de_la_decision(
    colaborador: httpx.AsyncClient, rrhh: httpx.AsyncClient, db_session: AsyncSession
) -> None:
    d = (await subir(colaborador)).json()
    url = f"{DESCANSOS}/{d['id']}/decision"

    casos = [
        ({"estado": "Rechazado"}, "comentario_requerido"),
        ({"estado": "Rechazado", "comentario_rrhh": "   "}, "comentario_requerido"),
        ({"estado": "Aprobado"}, "fechas_requeridas"),
        ({"estado": "Aprobado", "fecha_inicio": "2026-11-10"}, "fechas_requeridas"),
        (
            {"estado": "Aprobado", "fecha_inicio": "2026-11-10", "fecha_fin": "2026-11-09"},
            "validacion",
        ),
        ({"estado": "Pendiente"}, "validacion"),
        (
            {"estado": "Aprobado", "fecha_inicio": "10/11/2026", "fecha_fin": "2026-11-12"},
            "validacion",
        ),
    ]
    for cuerpo, codigo in casos:
        r = await rrhh.post(url, json=cuerpo)
        assert (r.status_code, r.json()["error"]["code"]) == (422, codigo), cuerpo

    ok = await rrhh.post(
        url,
        json={
            "estado": "Aprobado",
            "fecha_inicio": "2026-11-10",
            "fecha_fin": "2026-11-12",
            "comentario_rrhh": "  Conforme.  ",
        },
    )
    assert ok.status_code == 200, ok.text
    aprobado = ok.json()
    assert aprobado["estado"] == "Aprobado"
    assert (aprobado["fecha_inicio"], aprobado["fecha_fin"]) == ("2026-11-10", "2026-11-12")
    assert aprobado["comentario_rrhh"] == "Conforme."
    assert aprobado["decidido_at"] is not None
    assert aprobado["permisos"] == {
        "puede_analizar": False,
        "puede_decidir": False,
        "puede_eliminar": False,
    }

    repetida = await rrhh.post(url, json={"estado": "Rechazado", "comentario_rrhh": "No"})
    assert (repetida.status_code, repetida.json()["error"]["code"]) == (409, "descanso_ya_decidido")
    # El colaborador ve la decisión y ya no puede borrar.
    visto = (await colaborador.get(f"{DESCANSOS}/{d['id']}")).json()
    assert visto["estado"] == "Aprobado" and visto["comentario_rrhh"] == "Conforme."
    borrar = await colaborador.delete(f"{DESCANSOS}/{d['id']}")
    assert (borrar.status_code, borrar.json()["error"]["code"]) == (409, "descanso_no_pendiente")

    fila = await db_session.scalar(select(DescansoMedico))
    decisor = await db_session.scalar(select(User).where(User.dni == "33333333"))
    assert fila is not None and decisor is not None
    assert fila.decidido_por == decisor.id


async def test_rrhh_no_decide_su_propio_descanso(rrhh: httpx.AsyncClient) -> None:
    d = (await subir(rrhh)).json()
    assert d["permisos"] == {"puede_analizar": True, "puede_decidir": False, "puede_eliminar": True}
    r = await rrhh.post(
        f"{DESCANSOS}/{d['id']}/decision",
        json={"estado": "Aprobado", "fecha_inicio": "2026-11-10", "fecha_fin": "2026-11-12"},
    )
    assert (r.status_code, r.json()["error"]["code"]) == (403, "decision_propia_no_permitida")


async def test_dos_decisiones_simultaneas_solo_una_gana(
    app: FastAPI, colaborador: httpx.AsyncClient, db_session: AsyncSession
) -> None:
    d = (await subir(colaborador)).json()
    await create_user(db_session, "55555555", role="analista_rrhh")
    await create_user(db_session, "66666666", role="analista_rrhh")
    async with make_client(app) as a, make_client(app) as b:
        await login(a, "55555555")
        await login(b, "66666666")
        url = f"{DESCANSOS}/{d['id']}/decision"
        aprobar = {"estado": "Aprobado", "fecha_inicio": "2026-11-10", "fecha_fin": "2026-11-12"}
        rechazar = {"estado": "Rechazado", "comentario_rrhh": "Documento ilegible"}
        ra, rb = await asyncio.gather(a.post(url, json=aprobar), b.post(url, json=rechazar))
    assert sorted((ra.status_code, rb.status_code)) == [200, 409]
    decisiones = await db_session.scalar(
        select(func.count()).select_from(AuditLog).where(AuditLog.accion == "descanso_decidido")
    )
    assert decisiones == 1


# ---------- borrado ----------


async def test_el_dueno_elimina_un_pendiente_y_sus_archivos(
    app: FastAPI, colaborador: httpx.AsyncClient, db_session: AsyncSession
) -> None:
    d = (await subir(colaborador)).json()
    assert len(archivos_guardados(app)) == 2
    assert (await colaborador.delete(f"{DESCANSOS}/{d['id']}")).status_code == 204
    assert archivos_guardados(app) == []
    assert (await colaborador.get(f"{DESCANSOS}/{d['id']}")).status_code == 404
    assert (await colaborador.delete(f"{DESCANSOS}/{d['id']}")).status_code == 404


# ---------- colaboradores ----------


async def test_padron_con_filtros_y_facetas(
    rrhh: httpx.AsyncClient, colaborador: httpx.AsyncClient, otro_colaborador: httpx.AsyncClient
) -> None:
    todos = (await rrhh.get("/api/v1/colaboradores")).json()
    assert todos["total"] == 3
    assert [c["apellidos"] for c in todos["items"]] == ["Mora Paz", "Rojas Luna", "Salas Vera"]
    assert "password_hash" not in str(todos)

    assert (await rrhh.get("/api/v1/colaboradores", params={"q": "rojas"})).json()["total"] == 1
    assert (await rrhh.get("/api/v1/colaboradores", params={"q": "2222"})).json()["total"] == 1
    assert (await rrhh.get("/api/v1/colaboradores", params={"q": "%"})).json()["total"] == 0
    assert (await rrhh.get("/api/v1/colaboradores", params={"activo": "false"})).json()[
        "total"
    ] == 0
    assert (await rrhh.get("/api/v1/colaboradores", params={"categoria": "Z"})).status_code == 422

    facetas = (await rrhh.get("/api/v1/colaboradores/facetas")).json()
    assert facetas == {
        "areas_operacion": ["Operaciones"],
        "tipos_contrato": ["Indeterminado"],
        "sedes": ["Lima Centro"],
    }


# ---------- demo: aislamiento por visitante ----------


async def test_demo_aisla_a_cada_visitante(
    app_factory: AppFactory, make_settings: SettingsFactory, db_session: AsyncSession
) -> None:
    await demo.seed(db_session, make_settings(**DEMO_SETTINGS))
    overrides = DEMO_SETTINGS | {"demo_max_descansos_per_visitor": 2}
    async with app_factory(**overrides) as app, make_client(app) as v1, make_client(app) as v2:
        # Visitante 1 sube como colaborador de prueba.
        await login(v1, "10000001", "demo-colaborador")
        d = (await subir(v1)).json()
        assert (await subir(v1)).status_code == 201
        limite = await subir(v1)
        assert (limite.status_code, limite.json()["error"]["code"]) == (409, "limite_demo")

        # Visitante 2, con las mismas cuentas públicas, no ve nada de eso.
        await login(v2, "10000001", "demo-colaborador")
        assert (await v2.get(MIOS)).json()["total"] == 0
        assert (await v2.get(f"{DESCANSOS}/{d['id']}")).status_code == 404
        assert (await v2.get(f"{DESCANSOS}/{d['id']}/archivo")).status_code == 404
        assert (await v2.delete(f"{DESCANSOS}/{d['id']}")).status_code == 404
        assert (await subir(v2)).status_code == 201  # su cuota es propia

        await v2.post("/api/v1/auth/logout")
        await login(v2, "10000002", "demo-rrhh")
        vistos = (await v2.get(DESCANSOS)).json()
        assert vistos["total"] == 1  # solo lo que subió su propio navegador
        assert vistos["items"][0]["id"] != d["id"]
        decision = await v2.post(
            f"{DESCANSOS}/{d['id']}/decision",
            json={"estado": "Rechazado", "comentario_rrhh": "ajeno"},
        )
        assert decision.status_code == 404

        # El visitante 1 cambia a la cuenta de RRHH en el mismo navegador y sí puede revisar.
        await v1.post("/api/v1/auth/logout")
        await login(v1, "10000002", "demo-rrhh")
        propios = (await v1.get(DESCANSOS)).json()
        assert propios["total"] == 2
        ok = await v1.post(
            f"{DESCANSOS}/{d['id']}/decision",
            json={"estado": "Rechazado", "comentario_rrhh": "Prueba de rechazo"},
        )
        assert ok.status_code == 200


async def test_las_muestras_de_la_demo_son_de_solo_lectura(
    app_factory: AppFactory, make_settings: SettingsFactory, db_session: AsyncSession
) -> None:
    await demo.seed(db_session, make_settings(**DEMO_SETTINGS))
    async with app_factory(**DEMO_SETTINGS) as app, make_client(app) as cliente:
        await login(cliente, "10000001", "demo-colaborador")
        d = (await subir(cliente)).json()
        # Se convierte en muestra, como las que deja la siembra.
        await db_session.execute(update(DescansoMedico).values(es_muestra=True, visitor_id=None))
        await db_session.commit()

        muestra = (await cliente.get(f"{DESCANSOS}/{d['id']}")).json()
        assert muestra["es_muestra"] is True
        assert not any(muestra["permisos"].values())
        borrar = await cliente.delete(f"{DESCANSOS}/{d['id']}")
        assert (borrar.status_code, borrar.json()["error"]["code"]) == (403, "prohibido")

        await cliente.post("/api/v1/auth/logout")
        await login(cliente, "10000002", "demo-rrhh")
        decision = await cliente.post(
            f"{DESCANSOS}/{d['id']}/decision",
            json={"estado": "Rechazado", "comentario_rrhh": "no"},
        )
        assert (decision.status_code, decision.json()["error"]["code"]) == (403, "prohibido")
        # Cualquier otro visitante también ve la muestra.
        async with make_client(app) as otro:
            await login(otro, "10000002", "demo-rrhh")
            assert (await otro.get(DESCANSOS)).json()["total"] == 1


# ---------- purga ----------


async def test_purga_elimina_lo_caducado_de_la_demo_y_los_huerfanos(
    app_factory: AppFactory, make_settings: SettingsFactory, db_session: AsyncSession
) -> None:
    await demo.seed(db_session, make_settings(**DEMO_SETTINGS))
    async with app_factory(**DEMO_SETTINGS) as app, make_client(app) as cliente:
        await login(cliente, "10000001", "demo-colaborador")
        viejo = (await subir(cliente)).json()
        reciente = (await subir(cliente)).json()
        muestra = (await subir(cliente)).json()
        hace_dos_dias = datetime.now(UTC) - timedelta(days=2)
        await db_session.execute(
            update(DescansoMedico)
            .where(DescansoMedico.id.in_([viejo["id"], muestra["id"]]))
            .values(created_at=hace_dos_dias)
        )
        await db_session.execute(
            update(DescansoMedico)
            .where(DescansoMedico.id == muestra["id"])
            .values(es_muestra=True, visitor_id=None)
        )
        # Un análisis que quedó a medias por una caída del servidor.
        usuario = await db_session.scalar(select(User).where(User.dni == "10000001"))
        assert usuario is not None
        db_session.add(
            AnalisisDescanso(
                descanso_id=reciente["id"],
                solicitado_por=usuario.id,
                proveedor="fake",
                modelo="fake-1",
                estado="en_proceso",
                version_prompt="t",
                version_reglas="t",
                started_at=datetime.now(UTC) - timedelta(hours=1),
            )
        )
        await db_session.commit()

        # Un archivo huérfano antiguo (subida interrumpida) y otro recién escrito.
        storage = app.state.storage
        antiguo, nuevo = storage.new_prefix(), storage.new_prefix()
        await storage.put(antiguo, "original", b"x")
        await storage.put(nuevo, "original", b"x")
        import os

        marca = (datetime.now(UTC) - timedelta(hours=3)).timestamp()
        os.utime(storage.root / antiguo, (marca, marca))

        resultado = await purge_once(app.state.db, storage, app.state.settings)
        assert (resultado.descansos_demo, resultado.analisis_abandonados) == (1, 1)
        assert resultado.archivos_huerfanos == 1

        restantes = set(await db_session.scalars(select(DescansoMedico.id)))
        assert {str(i) for i in restantes} == {reciente["id"], muestra["id"]}
        assert not (storage.root / antiguo).exists()
        assert (storage.root / nuevo).exists()
        assert (await cliente.get(f"{DESCANSOS}/{viejo['id']}/paginas/1")).status_code == 404
        assert (await cliente.get(f"{DESCANSOS}/{reciente['id']}/paginas/1")).status_code == 200

        abandonado = await db_session.scalar(select(AnalisisDescanso))
        assert abandonado is not None
        await db_session.refresh(abandonado)
        assert (abandonado.estado, abandonado.error_code) == ("fallido", "abandonado")
        # Repetirla no encuentra nada más que hacer.
        assert not (await purge_once(app.state.db, storage, app.state.settings)).hubo_cambios()
