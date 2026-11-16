from __future__ import annotations

import argparse
import io
from datetime import UTC, date, datetime

import httpx
import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from humanaiz import cli
from humanaiz.config import ConfigError
from humanaiz.legal import TERMINOS_VERSION
from humanaiz.models import Colaborador, User, UserSession
from humanaiz.services import demo
from tests.conftest import (
    DEMO_SETTINGS,
    PASSWORD,
    AppFactory,
    SettingsFactory,
    create_user,
    credenciales,
    login,
    make_client,
)


async def test_config_publica_sin_demo(app_factory: AppFactory) -> None:
    async with app_factory() as app, make_client(app) as client:
        r = await client.get("/api/v1/config")
    assert r.status_code == 200
    cuerpo = r.json()
    assert cuerpo["demo"] == {
        "habilitado": False,
        "aviso": None,
        "usuarios": [],
        "retencion_horas": 24,
    }
    assert cuerpo["carga"] == {
        "max_bytes": 5 * 1024 * 1024,
        "tipos_mime": ["image/jpeg", "image/png", "image/webp"],
        "min_lado_px": 400,
        "max_lado_px": 2400,
    }
    proveedores = {p["id"]: p for p in cuerpo["llm"]["proveedores"]}
    assert set(proveedores) == {
        "anthropic",
        "openai",
        "gemini",
        "openrouter",
        "xai",
        "mistral",
        "groq",
    }
    for proveedor in proveedores.values():
        assert sum(m["predeterminado"] for m in proveedor["modelos"]) <= 1
        assert proveedor["url_claves"].startswith("https://")
    assert proveedores["anthropic"]["prefijos_clave"] == ["sk-ant-"]
    assert proveedores["groq"]["max_imagenes"] == 3


async def test_config_respeta_proveedores_habilitados(app_factory: AppFactory) -> None:
    async with (
        app_factory(llm_enabled_providers=("anthropic",)) as app,
        make_client(app) as client,
    ):
        r = await client.get("/api/v1/config")
    assert [p["id"] for p in r.json()["llm"]["proveedores"]] == ["anthropic"]


async def test_siembra_demo_es_idempotente_y_permite_entrar(
    app_factory: AppFactory, make_settings: SettingsFactory, db_session: AsyncSession
) -> None:
    settings = make_settings(**DEMO_SETTINGS)
    primera = await demo.seed(db_session, settings)
    segunda = await demo.seed(db_session, settings)
    assert primera == segunda
    assert await db_session.scalar(select(func.count()).select_from(User)) == 2
    assert await db_session.scalar(select(func.count()).select_from(Colaborador)) == 7

    async with app_factory(**DEMO_SETTINGS) as app, make_client(app) as client:
        config = (await client.get("/api/v1/config")).json()["demo"]
        assert config["habilitado"] is True
        assert "No subas documentos reales" in config["aviso"]
        for usuario in config["usuarios"]:
            sesion = await login(client, usuario["dni"], usuario["password"])
            assert sesion["usuario"]["is_demo"] is True
            assert sesion["usuario"]["role"] == usuario["role"]
            assert sesion["usuario"]["colaborador"] is not None


async def test_demo_y_usuarios_reales_son_excluyentes(
    app_factory: AppFactory, make_settings: SettingsFactory, db_session: AsyncSession
) -> None:
    await create_user(db_session, "12345678")
    with pytest.raises(ConfigError, match="usuarios reales"):
        await demo.seed(db_session, make_settings(**DEMO_SETTINGS))
    with pytest.raises(ConfigError, match="usuarios reales"):
        async with app_factory(**DEMO_SETTINGS):
            pass


async def test_sin_demo_no_arranca_con_cuentas_de_prueba_activas(
    app_factory: AppFactory, db_session: AsyncSession
) -> None:
    await create_user(db_session, "10000001", is_demo=True)
    with pytest.raises(ConfigError, match="cuentas de prueba activas"):
        async with app_factory():
            pass

    # Desactivarlas cierra sus sesiones y permite arrancar.
    assert await demo.disable(db_session) == 1
    assert await demo.disable(db_session) == 0
    async with app_factory() as app, make_client(app) as client:
        r = await client.post("/api/v1/auth/login", json=credenciales("10000001", PASSWORD))
        assert r.status_code == 401


def _args(**valores: object) -> argparse.Namespace:
    return argparse.Namespace(**valores)


async def test_cli_crea_usuario_y_cambia_su_password(
    make_settings: SettingsFactory, db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    settings = make_settings()
    db_session.add(
        Colaborador(
            dni="12345678",
            nombres="Ana",
            apellidos="Pérez",
            fecha_nacimiento=date(1990, 1, 1),
            categoria="A",
            sexo="F",
            area_operacion="RRHH",
            tipo_contrato="Indeterminado",
            sede="Lima",
        )
    )
    await db_session.commit()

    crear = _args(
        dni="12345678", nombres="Ana", apellidos="Pérez", role="analista_rrhh", password_stdin=True
    )
    monkeypatch.setattr("sys.stdin", io.StringIO("corta\n"))
    assert await cli._create_user(crear, settings) == 2
    monkeypatch.setattr("sys.stdin", io.StringIO("una-clave-larga-y-buena\n"))
    assert await cli._create_user(crear, settings) == 0
    monkeypatch.setattr("sys.stdin", io.StringIO("una-clave-larga-y-buena\n"))
    assert await cli._create_user(crear, settings) == 2  # duplicado

    user = await db_session.scalar(select(User).where(User.dni == "12345678"))
    assert user is not None
    assert user.password_hash.startswith("$argon2id$")
    colaborador = await db_session.scalar(select(Colaborador).where(Colaborador.dni == "12345678"))
    assert colaborador is not None
    assert colaborador.user_id == user.id

    db_session.add(
        UserSession(
            user_id=user.id,
            token_hash=b"h" * 32,
            expires_at=datetime(2999, 1, 1, tzinfo=UTC),
        )
    )
    await db_session.commit()
    monkeypatch.setattr("sys.stdin", io.StringIO("otra-clave-larga-distinta\n"))
    assert await cli._set_password(_args(dni="12345678", password_stdin=True), settings) == 0
    await db_session.refresh(user)
    sesion = await db_session.scalar(select(UserSession))
    assert sesion is not None
    await db_session.refresh(sesion)
    assert sesion.revoked_at is not None


async def test_cli_no_crea_usuarios_reales_en_modo_demo(make_settings: SettingsFactory) -> None:
    crear = _args(
        dni="12345678", nombres="A", apellidos="B", role="colaborador", password_stdin=True
    )
    assert await cli._create_user(crear, make_settings(**DEMO_SETTINGS)) == 2


async def test_cli_importa_colaboradores(
    make_settings: SettingsFactory, db_session: AsyncSession, tmp_path
) -> None:
    await create_user(db_session, "12345678", con_colaborador=False)
    csv_path = tmp_path / "padron.csv"
    cabecera = ",".join(cli._COLUMNAS_CSV)
    csv_path.write_text(
        f"{cabecera}\n"
        "12345678,Pérez Gómez,Ana María,1990-01-15,B,F,999888777,Operaciones,Indeterminado,Lima,si\n"
        "87654321,Ruiz Díaz,Juan,1988-06-30,C,M,,Ventas,Plazo fijo,Cusco,no\n",
        encoding="utf-8",
    )
    assert await cli._import_colaboradores(_args(archivo=str(csv_path)), make_settings()) == 0
    assert await cli._import_colaboradores(_args(archivo=str(csv_path)), make_settings()) == 0

    filas = (await db_session.scalars(select(Colaborador).order_by(Colaborador.dni))).all()
    assert [(c.dni, c.activo, c.user_id is not None) for c in filas] == [
        ("12345678", True, True),
        ("87654321", False, False),
    ]

    csv_path.write_text(f"{cabecera}\n1234,X,Y,1990-01-15,B,F,,A,B,C,si\n", encoding="utf-8")
    assert await cli._import_colaboradores(_args(archivo=str(csv_path)), make_settings()) == 2


async def test_muestras_de_la_demo_con_analisis_en_los_tres_estados(
    app_factory: AppFactory, make_settings: SettingsFactory, db_session: AsyncSession
) -> None:
    settings = make_settings(**DEMO_SETTINGS)
    from humanaiz.storage.local import LocalStorage

    storage = LocalStorage(settings.storage_local_path)
    primera = await demo.seed(db_session, settings, storage)
    assert primera.muestras == 3
    assert (await demo.seed(db_session, settings, storage)).muestras == 0  # idempotente

    async with app_factory(**DEMO_SETTINGS) as app, make_client(app) as cliente:
        await login(cliente, "10000002", "demo-rrhh")
        todos = (await cliente.get("/api/v1/descansos")).json()
        assert todos["total"] == 3
        por_estado = {d["ultimo_analisis"]["estado_documento"]: d for d in todos["items"]}
        assert set(por_estado) == {"Aprobado", "Observado", "Rechazado"}
        for d in todos["items"]:
            assert d["es_muestra"] is True
            assert not any(d["permisos"].values())
            assert d["ultimo_analisis"]["proveedor"] == "muestra"
            pagina = await cliente.get(f"/api/v1/descansos/{d['id']}/paginas/1")
            assert pagina.status_code == 200 and pagina.headers["content-type"] == "image/jpeg"
        assert por_estado["Aprobado"]["estado"] == "Aprobado"
        assert por_estado["Aprobado"]["fecha_inicio"] is not None
        assert por_estado["Rechazado"]["ultimo_analisis"]["motivos_rechazo"] == [
            "El DNI del documento no coincide con el del colaborador."
        ]
        observado = {
            v["codigo"]: v["resultado"]
            for v in por_estado["Observado"]["ultimo_analisis"]["validaciones_detalle"]
        }
        assert observado["dias_coinciden"] == "falla"
        assert observado["codigo_medico_presente"] == "falla"

        # El colaborador de prueba ve su propia muestra en "Mis descansos".
        await cliente.post("/api/v1/auth/logout")
        await login(cliente, "10000001", "demo-colaborador")
        mios = (await cliente.get("/api/v1/me/descansos")).json()
        assert [d["estado"] for d in mios["items"]] == ["Aprobado"]


async def test_config_publica_expone_los_datos_del_proyecto(app_factory: AppFactory) -> None:
    async with app_factory() as app, make_client(app) as client:
        sin_datos = (await client.get("/api/v1/config")).json()["proyecto"]
    assert sin_datos == {
        "concurso": None,
        "puesto": None,
        "contacto": None,
        "version_terminos": TERMINOS_VERSION,
        "retencion_registros_dias": 30,
    }
    overrides = {
        "concurso_nombre": "  Hackatón de Prueba 2026 ",
        "concurso_puesto": 1,
        "contacto_proyecto": "equipo@example.com",
        "audit_retention_days": 7,
        "demo_ttl_hours": 12,
    }
    async with app_factory(**overrides) as app, make_client(app) as client:
        cuerpo = (await client.get("/api/v1/config")).json()
    assert cuerpo["proyecto"]["concurso"] == "Hackatón de Prueba 2026"
    assert cuerpo["proyecto"]["puesto"] == 1
    assert cuerpo["proyecto"]["contacto"] == "equipo@example.com"
    assert cuerpo["proyecto"]["retencion_registros_dias"] == 7
    assert cuerpo["demo"]["retencion_horas"] == 12


async def test_purga_borra_la_bitacora_antigua(
    app_factory: AppFactory, db_session: AsyncSession
) -> None:
    from datetime import timedelta

    from humanaiz.models import AuditLog
    from humanaiz.tasks import purge_once

    ahora = datetime.now(UTC)
    db_session.add_all(
        [
            AuditLog(accion="login", at=ahora - timedelta(days=40), ip="203.0.113.1"),
            AuditLog(accion="login", at=ahora - timedelta(days=2), ip="203.0.113.2"),
        ]
    )
    await db_session.commit()
    async with app_factory(audit_retention_days=30) as app:
        resultado = await purge_once(app.state.db, app.state.storage, app.state.settings)
    assert resultado.registros_auditoria == 1
    restantes = (await db_session.scalars(select(AuditLog.ip))).all()
    assert [str(ip) for ip in restantes] == ["203.0.113.2"]


async def test_certificados_de_ejemplo_para_probar_la_lectura(
    app_factory: AppFactory, make_settings: SettingsFactory, db_session: AsyncSession
) -> None:
    import io

    from PIL import Image

    await demo.seed(db_session, make_settings(**DEMO_SETTINGS))
    async with app_factory(**DEMO_SETTINGS) as app, make_client(app) as cliente:
        assert (await cliente.get("/api/v1/demo/certificados/valido")).status_code == 401
        await login(cliente, "10000001", "demo-colaborador")
        for variante in ("valido", "observado", "otra-persona", "citt"):
            r = await cliente.get(f"/api/v1/demo/certificados/{variante}")
            assert r.status_code == 200, (variante, r.text)
            assert r.headers["content-type"] == "image/jpeg"
            assert r.headers["content-disposition"].startswith("attachment;")
            assert "sandbox" in r.headers["content-security-policy"]
            imagen = Image.open(io.BytesIO(r.content))
            assert imagen.size == (1240, 1754)
        assert (await cliente.get("/api/v1/demo/certificados/inventado")).status_code == 422

        # El certificado generado se puede subir: es un documento válido para la aplicación.
        subida = await cliente.post(
            "/api/v1/descansos",
            files={"archivo": ("ejemplo.jpg", r.content, "image/jpeg")},
        )
        assert subida.status_code == 201, subida.text


async def test_sin_modo_demo_no_hay_certificados_de_ejemplo(
    client: httpx.AsyncClient, db_session: AsyncSession
) -> None:
    await create_user(db_session, "12345678")
    await login(client, "12345678")
    r = await client.get("/api/v1/demo/certificados/valido")
    assert (r.status_code, r.json()["error"]["code"]) == (404, "no_encontrado")


async def test_cli_retira_un_descanso_y_su_imagen_de_inmediato(
    app_factory: AppFactory, db_session: AsyncSession
) -> None:
    """Ante una denuncia no hace falta esperar a la purga de 24 horas."""
    from humanaiz.models import AuditLog, DescansoMedico
    from tests import files

    await create_user(db_session, "12345678")
    async with app_factory() as app, make_client(app) as cliente:
        await login(cliente, "12345678")
        subida = await cliente.post(
            "/api/v1/descansos",
            data={"sede": "Lima"},
            files={"archivo": ("c.jpg", files.jpeg_bytes(), "image/jpeg")},
        )
        descanso_id = subida.json()["id"]
        raiz = app.state.settings.storage_local_path
        assert any(p.is_file() for p in raiz.rglob("*"))

        settings = app.state.settings
        assert await cli._delete_descanso(_args(id="no-es-uuid", motivo="otro"), settings) == 2
        args = _args(id=descanso_id, motivo="contenido_indebido")
        assert await cli._delete_descanso(args, settings) == 0
        assert await cli._delete_descanso(args, settings) == 2  # ya no existe

        assert not any(p.is_file() for p in raiz.rglob("*"))
        assert await db_session.scalar(select(func.count()).select_from(DescansoMedico)) == 0
        assert (await cliente.get(f"/api/v1/descansos/{descanso_id}")).status_code == 404
        retirado = await db_session.scalar(
            select(AuditLog).where(AuditLog.accion == "descanso_retirado")
        )
        assert retirado is not None and retirado.detalle == {"motivo": "contenido_indebido"}
