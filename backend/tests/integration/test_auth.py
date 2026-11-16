from __future__ import annotations

import time
import uuid
from datetime import UTC, datetime, timedelta

import httpx
import jwt
from fastapi import FastAPI
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from humanaiz.legal import TERMINOS_VERSION
from humanaiz.models import AuditLog, User, UserSession
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

LOGIN = "/api/v1/auth/login"
REFRESH = "/api/v1/auth/refresh"
LOGOUT = "/api/v1/auth/logout"
ME = "/api/v1/auth/me"
COOKIE = "__Host-hz_session"


async def test_login_devuelve_sesion_y_cookie_segura(
    client: httpx.AsyncClient, db_session: AsyncSession
) -> None:
    await create_user(db_session, "12345678", role="analista_rrhh")
    r = await client.post(LOGIN, json=credenciales("12345678", PASSWORD))
    assert r.status_code == 200
    body = r.json()
    assert body["token_type"] == "bearer"
    assert body["expires_in"] == 900
    assert body["usuario"]["role"] == "analista_rrhh"
    assert body["usuario"]["colaborador"]["sede"] == "Lima Centro"
    assert "password" not in r.text

    cookie = r.headers["set-cookie"]
    assert cookie.startswith(f"{COOKIE}=")
    for atributo in ("HttpOnly", "Secure", "SameSite=strict", "Path=/"):
        assert atributo in cookie
    assert "Domain" not in cookie

    # El token de la cookie no se guarda en claro: solo su hash.
    fila = await db_session.scalar(select(UserSession))
    assert fila is not None
    assert len(fila.token_hash) == 32
    assert client.cookies[COOKIE].encode() != fila.token_hash


async def test_ciclo_login_me_refresh_logout(
    client: httpx.AsyncClient, db_session: AsyncSession
) -> None:
    await create_user(db_session, "12345678")
    await login(client, "12345678")

    me = await client.get(ME)
    assert me.status_code == 200
    assert me.json()["dni"] == "12345678"

    del client.headers["Authorization"]
    renovado = await client.post(REFRESH)
    assert renovado.status_code == 200
    assert renovado.json()["usuario"]["dni"] == "12345678"

    assert (await client.post(LOGOUT)).status_code == 204
    tras_logout = await client.post(REFRESH)
    assert tras_logout.status_code == 401
    assert tras_logout.json()["error"]["code"] == "sesion_invalida"
    # Repetir el logout no falla.
    assert (await client.post(LOGOUT)).status_code == 204


async def test_refresh_con_cookie_invalida_la_borra(client: httpx.AsyncClient) -> None:
    client.cookies.set(COOKIE, "token-inventado", domain="humanaiz.test")
    r = await client.post(REFRESH)
    assert r.status_code == 401
    assert f'{COOKIE}=""' in r.headers["set-cookie"] or f"{COOKIE}=;" in r.headers["set-cookie"]
    assert "Max-Age=0" in r.headers["set-cookie"]


async def test_sin_origin_correcto_se_rechaza(
    app: FastAPI, client: httpx.AsyncClient, db_session: AsyncSession
) -> None:
    await create_user(db_session, "12345678")
    cuerpo = credenciales("12345678", PASSWORD)
    for origen in ("https://malicioso.example", "https://sub.humanaiz.test", None):
        cabeceras = {"Origin": origen} if origen else {}
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="https://humanaiz.test"
        ) as otro:
            for ruta, datos in ((LOGIN, cuerpo), (REFRESH, None), (LOGOUT, None)):
                r = await otro.post(ruta, json=datos, headers=cabeceras)
                assert r.status_code == 403, (origen, ruta)
                assert r.json()["error"]["code"] == "origen_invalido"


async def test_credenciales_invalidas_no_distinguen_el_motivo(
    client: httpx.AsyncClient, db_session: AsyncSession
) -> None:
    await create_user(db_session, "12345678")
    await create_user(db_session, "87654321", is_active=False)

    inicio = time.perf_counter()
    mala = await client.post(LOGIN, json=credenciales("12345678", "incorrecta"))
    t_mala = time.perf_counter() - inicio
    inicio = time.perf_counter()
    inexistente = await client.post(LOGIN, json=credenciales("00000000", "incorrecta"))
    t_inexistente = time.perf_counter() - inicio
    inactiva = await client.post(LOGIN, json=credenciales("87654321", PASSWORD))

    for r in (mala, inexistente, inactiva):
        assert r.status_code == 401
        assert r.json()["error"]["code"] == "credenciales_invalidas"
        assert "set-cookie" not in r.headers
    assert mala.json()["error"]["message"] == inexistente.json()["error"]["message"]
    # Con DNI inexistente también se verifica un hash: no responde "al instante".
    assert t_inexistente > t_mala * 0.4

    fallidos = (
        await db_session.scalars(select(AuditLog).where(AuditLog.accion == "login_fallido"))
    ).all()
    assert len(fallidos) == 3


async def test_login_valida_formato_sin_reflejar_la_entrada(client: httpx.AsyncClient) -> None:
    # Valores que no pueden aparecer por azar en el request_id (hexadecimal).
    r = await client.post(LOGIN, json=credenciales("xyz", "secreto-que-no-debe-volver"))
    assert r.status_code == 422
    assert r.json()["error"]["code"] == "validacion"
    assert "secreto-que-no-debe-volver" not in r.text
    assert "xyz" not in r.text


async def test_limite_de_intentos_de_login(
    app_factory: AppFactory, db_session: AsyncSession
) -> None:
    await create_user(db_session, "12345678")
    async with app_factory(rate_limit_login="5/minute") as app, make_client(app) as client:
        cuerpo = credenciales("12345678", "incorrecta")
        codigos = [(await client.post(LOGIN, json=cuerpo)).status_code for _ in range(5)]
        assert codigos == [401] * 5
        bloqueado = await client.post(LOGIN, json=cuerpo)
        assert bloqueado.status_code == 429
        assert bloqueado.json()["error"]["code"] == "rate_limit"
        assert int(bloqueado.headers["retry-after"]) >= 1
        # Ni la contraseña correcta pasa mientras dura el bloqueo...
        assert (
            await client.post(LOGIN, json=credenciales("12345678", PASSWORD))
        ).status_code == 429
        # ...pero otra IP con el mismo DNI no queda bloqueada: no se bloquea la cuenta.
        async with make_client(app, ip="198.51.100.7") as otra_ip:
            ok = await otra_ip.post(LOGIN, json=credenciales("12345678", PASSWORD))
            assert ok.status_code == 200


async def test_rotar_ip_no_permite_probar_contrasenas_sin_fin(
    app_factory: AppFactory, db_session: AsyncSession
) -> None:
    """Con VPN o proxies cada intento llega desde otra IP: el tope por DNI lo frena."""
    await create_user(db_session, "12345678")
    async with app_factory(rate_limit_login_dni="3/hour") as app:
        codigos = []
        for n in range(4):
            async with make_client(app, ip=f"198.51.100.{n + 1}") as cliente:
                r = await cliente.post(LOGIN, json=credenciales("12345678", "incorrecta"))
                codigos.append(r.status_code)
        assert codigos == [401, 401, 401, 429]


async def test_el_tope_por_dni_no_aplica_a_las_cuentas_publicas_de_la_demo(
    app_factory: AppFactory, make_settings: SettingsFactory, db_session: AsyncSession
) -> None:
    await demo.seed(db_session, make_settings(**DEMO_SETTINGS))
    async with app_factory(**DEMO_SETTINGS, rate_limit_login_dni="1/hour") as app:
        for n in range(3):
            async with make_client(app, ip=f"198.51.100.{n + 1}") as cliente:
                r = await cliente.post(LOGIN, json=credenciales("10000001", "demo-colaborador"))
                assert r.status_code == 200, r.text


async def test_cerrar_una_sesion_no_cierra_las_demas(
    app: FastAPI, db_session: AsyncSession
) -> None:
    await create_user(db_session, "12345678")
    async with make_client(app) as a, make_client(app) as b:
        await login(a, "12345678")
        await login(b, "12345678")
        assert (await a.post(LOGOUT)).status_code == 204
        assert (await b.post(REFRESH)).status_code == 200
        assert (await a.post(REFRESH)).status_code == 401


async def test_usuario_desactivado_pierde_acceso_de_inmediato(
    client: httpx.AsyncClient, db_session: AsyncSession
) -> None:
    user = await create_user(db_session, "12345678")
    await login(client, "12345678")
    await db_session.execute(update(User).where(User.id == user.id).values(is_active=False))
    await db_session.commit()

    r = await client.get(ME)
    assert r.status_code == 401
    assert r.json()["error"]["code"] == "sesion_invalida"
    assert (await client.post(REFRESH)).status_code == 401


async def test_sesion_caducada_por_inactividad_o_tiempo_total(
    client: httpx.AsyncClient, db_session: AsyncSession
) -> None:
    await create_user(db_session, "12345678")
    await login(client, "12345678")
    hace_mucho = datetime.now(UTC) - timedelta(days=2)
    await db_session.execute(update(UserSession).values(last_used_at=hace_mucho))
    await db_session.commit()
    assert (await client.post(REFRESH)).status_code == 401

    await login(client, "12345678")
    await db_session.execute(update(UserSession).values(expires_at=hace_mucho))
    await db_session.commit()
    assert (await client.post(REFRESH)).status_code == 401


async def test_tokens_de_acceso_invalidos(
    app: FastAPI, client: httpx.AsyncClient, db_session: AsyncSession
) -> None:
    user = await create_user(db_session, "12345678")
    secreto = app.state.settings.jwt_secret.get_secret_value()
    ahora = datetime.now(UTC)
    base = {"sub": str(user.id), "sid": str(uuid.uuid4()), "aud": "humanaiz-api", "iat": ahora}

    caducado = jwt.encode(base | {"exp": ahora - timedelta(minutes=1)}, secreto, "HS256")
    r = await client.get(ME, headers={"Authorization": f"Bearer {caducado}"})
    assert (r.status_code, r.json()["error"]["code"]) == (401, "token_expirado")

    otro_secreto = jwt.encode(base | {"exp": ahora + timedelta(minutes=5)}, "x" * 48, "HS256")
    sin_firma = jwt.encode(base | {"exp": ahora + timedelta(minutes=5)}, "", "none")
    otra_audiencia = jwt.encode(
        base | {"aud": "otra", "exp": ahora + timedelta(minutes=5)}, secreto, "HS256"
    )
    for token in (otro_secreto, sin_firma, otra_audiencia, "no-es-un-jwt"):
        r = await client.get(ME, headers={"Authorization": f"Bearer {token}"})
        assert (r.status_code, r.json()["error"]["code"]) == (401, "no_autenticado")

    assert (await client.get(ME)).status_code == 401


async def test_demo_asigna_y_conserva_el_visitante(
    app_factory: AppFactory, db_session: AsyncSession
) -> None:
    await create_user(db_session, "10000001", is_demo=True)
    await create_user(db_session, "10000002", is_demo=True, role="analista_rrhh")
    async with app_factory(**DEMO_SETTINGS) as app, make_client(app) as client:
        primera = await login(client, "10000001")
        visitante = client.cookies["__Host-hz_visitor"]
        uuid.UUID(visitante)
        claims = jwt.decode(primera["access_token"], options={"verify_signature": False})
        assert claims["vid"] == visitante

        # Cerrar sesión y entrar con la otra cuenta conserva el mismo visitante.
        await client.post(LOGOUT)
        segunda = await login(client, "10000002")
        claims = jwt.decode(segunda["access_token"], options={"verify_signature": False})
        assert claims["vid"] == visitante

        # Otro navegador recibe un visitante distinto.
        async with make_client(app) as otro:
            await login(otro, "10000001")
            assert otro.cookies["__Host-hz_visitor"] != visitante


async def test_login_exige_aceptar_los_terminos_vigentes(
    client: httpx.AsyncClient, db_session: AsyncSession
) -> None:
    await create_user(db_session, "12345678")
    base = credenciales("12345678")

    sin_aceptar = await client.post(LOGIN, json=base | {"acepta_terminos": False})
    assert (sin_aceptar.status_code, sin_aceptar.json()["error"]["code"]) == (
        422,
        "terminos_requeridos",
    )
    omitido = await client.post(LOGIN, json={"dni": "12345678", "password": PASSWORD})
    assert omitido.json()["error"]["code"] == "terminos_requeridos"

    antigua = await client.post(LOGIN, json=base | {"terminos_version": "2000-01-01"})
    assert (antigua.status_code, antigua.json()["error"]["code"]) == (
        409,
        "terminos_desactualizados",
    )
    for r in (sin_aceptar, omitido, antigua):
        assert "set-cookie" not in r.headers

    ok = await client.post(LOGIN, json=base)
    assert ok.status_code == 200
    registro = await db_session.scalar(select(AuditLog).where(AuditLog.accion == "login"))
    assert registro is not None
    assert registro.detalle == {"terminos_version": TERMINOS_VERSION}
