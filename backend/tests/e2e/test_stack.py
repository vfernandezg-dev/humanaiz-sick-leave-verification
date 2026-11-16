"""Pruebas de extremo a extremo contra el stack real de docker compose.

Verifican lo que solo existe con todas las piezas juntas: cabeceras del proxy,
límites de cuerpo, rutas internas ocultas y, sobre todo, que la clave de IA no
queda en logs, base de datos ni archivos.

Requisitos: stack levantado en modo demo (`docker compose up -d --wait` con
DEMO_MODE=true en el .env de la raíz) y salida a internet.

    cd backend && uv run pytest -m e2e tests/e2e

Variables opcionales: E2E_BASE_URL (por defecto, PUBLIC_ORIGIN del .env).
"""

from __future__ import annotations

import io
import os
import re
import subprocess
import uuid
from collections.abc import Iterator
from pathlib import Path

import httpx
import pytest
from PIL import Image, ImageDraw

from humanaiz.legal import TERMINOS_VERSION

pytestmark = pytest.mark.e2e

RAIZ = Path(__file__).resolve().parents[3]
CANARIO = f"sk-ant-CANARIO-{uuid.uuid4().hex}{uuid.uuid4().hex}"


def _env_raiz() -> dict[str, str]:
    valores: dict[str, str] = {}
    archivo = RAIZ / ".env"
    if archivo.exists():
        for linea in archivo.read_text(encoding="utf-8").splitlines():
            if "=" in linea and not linea.lstrip().startswith("#"):
                clave, _, valor = linea.partition("=")
                valores[clave.strip()] = valor.strip()
    return valores


ENV = _env_raiz()
BASE = os.environ.get("E2E_BASE_URL", ENV.get("PUBLIC_ORIGIN", "https://localhost")).rstrip("/")
API = f"{BASE}/api/v1"


def compose(*args: str, entrada: bytes | None = None) -> str:
    resultado = subprocess.run(
        ["docker", "compose", *args],
        cwd=RAIZ,
        input=entrada,
        capture_output=True,
        timeout=120,
        check=False,
    )
    return (resultado.stdout + resultado.stderr).decode("utf-8", "replace")


def psql(sql: str) -> str:
    return compose(
        "exec", "-T", "db", "sh", "-c", 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Atc "$0"', sql
    ).strip()


def certificado() -> bytes:
    imagen = Image.new("RGB", (900, 1200), (250, 250, 245))
    ImageDraw.Draw(imagen).text(
        (60, 60), "CERTIFICADO DE PRUEBA E2E - DATOS FICTICIOS", fill=(0, 0, 0)
    )
    buffer = io.BytesIO()
    imagen.save(buffer, "JPEG", quality=85)
    return buffer.getvalue()


def cliente() -> httpx.Client:
    # verify=False: en local Caddy usa su propia autoridad certificadora.
    return httpx.Client(base_url=BASE, verify=False, headers={"Origin": BASE}, timeout=150)  # noqa: S501


def entrar(c: httpx.Client, rol: str) -> None:
    prefijo = "DEMO_COLABORADOR" if rol == "colaborador" else "DEMO_RRHH"
    r = c.post(
        "/api/v1/auth/login",
        json={
            "dni": ENV[f"{prefijo}_DNI"],
            "password": ENV[f"{prefijo}_PASSWORD"],
            "acepta_terminos": True,
            "terminos_version": TERMINOS_VERSION,
        },
    )
    assert r.status_code == 200, r.text
    c.headers["Authorization"] = f"Bearer {r.json()['access_token']}"


@pytest.fixture(scope="module", autouse=True)
def stack_disponible() -> None:
    if ENV.get("DEMO_MODE", "").lower() != "true":
        pytest.skip("El stack debe estar en modo demo (DEMO_MODE=true en el .env de la raíz).")
    try:
        with cliente() as c:
            c.get("/api/v1/health/live").raise_for_status()
    except httpx.HTTPError as exc:
        pytest.skip(f"El stack no responde en {BASE}: {type(exc).__name__}")


@pytest.fixture(scope="module")
def colaborador(stack_disponible: None) -> Iterator[httpx.Client]:
    # Una sola sesión para todo el módulo: el límite real de inicios de sesión
    # (5 por minuto por IP y DNI) también aplica a estas pruebas.
    with cliente() as c:
        entrar(c, "colaborador")
        yield c


def subir(c: httpx.Client) -> str:
    r = c.post(
        "/api/v1/descansos",
        files={"archivo": ("cert.jpg", certificado(), "image/jpeg")},
        data={"sede": "Lima Centro"},
    )
    assert r.status_code == 201, r.text
    return r.json()["id"]


def test_cabeceras_de_seguridad() -> None:
    with cliente() as c:
        pagina = c.get("/")
        api = c.get("/api/v1/health/live")
    csp = pagina.headers["content-security-policy"]
    for directiva in (
        "default-src 'none'",
        "script-src 'self'",
        "connect-src 'self'",
        "frame-ancestors 'none'",
        "base-uri 'none'",
    ):
        assert directiva in csp
    assert "unsafe-eval" not in csp
    assert "'unsafe-inline'" not in csp.split("script-src")[1].split(";")[0]
    for respuesta in (pagina, api):
        assert respuesta.headers["x-content-type-options"] == "nosniff"
        assert respuesta.headers["x-frame-options"] == "DENY"
        assert respuesta.headers["referrer-policy"] == "no-referrer"
        assert "max-age=" in respuesta.headers["strict-transport-security"]
        assert "server" not in respuesta.headers
    assert api.headers["cache-control"] == "no-store"
    assert pagina.headers["cache-control"] == "no-cache"


def test_rutas_internas_no_se_exponen() -> None:
    with cliente() as c:
        for ruta in ("/api/v1/health/ready", "/api/docs", "/api/openapi.json"):
            assert c.get(ruta).status_code == 404, ruta
        # Una ruta cualquiera del SPA devuelve la aplicación, no un 404 del proxy.
        assert '<div id="root">' in c.get("/rrhh/descansos").text


def test_cookie_de_sesion_inaccesible_para_scripts() -> None:
    with cliente() as c:
        r = c.post(
            "/api/v1/auth/login",
            json={
                "dni": ENV["DEMO_COLABORADOR_DNI"],
                "password": ENV["DEMO_COLABORADOR_PASSWORD"],
                "acepta_terminos": True,
                "terminos_version": TERMINOS_VERSION,
            },
        )
    sesion = next(v for v in r.headers.get_list("set-cookie") if "hz_session" in v)
    assert sesion.startswith("__Host-hz_session=")
    for atributo in ("HttpOnly", "Secure", "SameSite=strict", "Path=/"):
        assert atributo in sesion
    assert "Domain=" not in sesion


def test_origen_distinto_no_puede_usar_la_sesion() -> None:
    with cliente() as c:
        entrar(c, "colaborador")
        r = c.post("/api/v1/auth/refresh", headers={"Origin": "https://otro.example"})
        assert (r.status_code, r.json()["error"]["code"]) == (403, "origen_invalido")
        assert c.post("/api/v1/auth/refresh").status_code == 200


def _estado_con_curl(ruta: str, archivo: Path, token: str) -> str:
    # Con curl y no con httpx: el proxy responde 413 antes de recibir todo el
    # cuerpo, y curl sí atiende esa respuesta anticipada.
    resultado = subprocess.run(
        [
            "curl",
            "-sk",
            "-o",
            os.devnull,
            "-w",
            "%{http_code}",
            "--max-time",
            "60",
            "-X",
            "POST",
            "-H",
            f"Origin: {BASE}",
            "-H",
            f"Authorization: Bearer {token}",
            "-H",
            "Content-Type: application/octet-stream",
            "--data-binary",
            f"@{archivo}",
            f"{BASE}{ruta}",
        ],
        capture_output=True,
        timeout=90,
        check=False,
    )
    return resultado.stdout.decode().strip()


def test_limites_de_cuerpo_en_el_proxy(colaborador: httpx.Client, tmp_path: Path) -> None:
    token = colaborador.headers["Authorization"].removeprefix("Bearer ")
    grande = tmp_path / "grande.bin"
    grande.write_bytes(b"0" * (11 * 1024 * 1024))
    mediano = tmp_path / "mediano.bin"
    mediano.write_bytes(b"0" * 70_000)
    # La subida admite hasta ~10 MB; el resto de la API, 64 KB.
    assert _estado_con_curl("/api/v1/descansos", grande, token) == "413"
    assert _estado_con_curl("/api/v1/auth/logout", mediano, token) == "413"
    # La sesión sigue viva: el proxy cortó antes de llegar a la API.
    assert colaborador.get("/api/v1/auth/me").status_code == 200


def test_aislamiento_entre_visitantes_de_la_demo(colaborador: httpx.Client) -> None:
    descanso_id = subir(colaborador)
    with cliente() as otro_navegador:
        entrar(otro_navegador, "rrhh")
        assert otro_navegador.get(f"/api/v1/descansos/{descanso_id}").status_code == 404
        ids = {d["id"] for d in otro_navegador.get("/api/v1/descansos?limit=200").json()["items"]}
        assert descanso_id not in ids
    assert colaborador.delete(f"/api/v1/descansos/{descanso_id}").status_code == 204


def test_canario_la_clave_no_queda_en_logs_base_de_datos_ni_archivos(
    colaborador: httpx.Client,
) -> None:
    descanso_id = subir(colaborador)
    try:
        for proveedor in ("anthropic", "openai", "gemini"):
            r = colaborador.post(
                f"/api/v1/descansos/{descanso_id}/analisis",
                json={"proveedor": proveedor},
                headers={"X-LLM-Api-Key": CANARIO},
            )
            # La clave es inventada: el proveedor real la rechaza (400). Sin salida
            # a internet sería un 502; en ningún caso un 5xx sin explicación.
            assert r.status_code in (400, 502), r.text
            assert r.json()["error"]["code"].startswith("llm_")
            assert CANARIO not in r.text
        # También en la ruta feliz de lectura posterior.
        assert CANARIO not in colaborador.get(f"/api/v1/descansos/{descanso_id}").text

        assert CANARIO not in compose("logs", "--no-color"), "la clave aparece en los logs"
        volcado = compose(
            "exec", "-T", "db", "sh", "-c", 'pg_dump -U "$POSTGRES_USER" "$POSTGRES_DB"'
        )
        assert "analisis_descanso" in volcado  # el volcado es real
        assert CANARIO not in volcado, "la clave aparece en la base de datos"
        encontrados = compose(
            "exec",
            "-T",
            "api",
            "sh",
            "-c",
            'grep -rl "$0" /data/uploads /tmp 2>/dev/null | wc -l',
            CANARIO,
        ).strip()
        assert encontrados == "0", "la clave aparece en disco"
    finally:
        colaborador.delete(f"/api/v1/descansos/{descanso_id}")


def test_la_purga_elimina_lo_caducado_de_la_demo(colaborador: httpx.Client) -> None:
    descanso_id = subir(colaborador)
    prefijo = psql(f"select archivo_key from descansos_medicos where id = '{descanso_id}'")
    assert prefijo
    psql(
        "update descansos_medicos set created_at = now() - interval '30 days' "
        f"where id = '{descanso_id}'"
    )
    salida = compose("exec", "-T", "api", "humanaiz", "purge")
    assert "Purga:" in salida, salida
    assert colaborador.get(f"/api/v1/descansos/{descanso_id}").status_code == 404
    restantes = compose(
        "exec", "-T", "api", "sh", "-c", 'ls "/data/uploads/$0" 2>/dev/null | wc -l', prefijo
    ).strip()
    assert restantes == "0"
    # Las muestras de la demo no caducan.
    assert int(psql("select count(*) from descansos_medicos where es_muestra")) == 3


def test_contenedores_endurecidos() -> None:
    assert compose("exec", "-T", "api", "id", "-u").strip() == "10001"
    assert "Read-only file system" in compose("exec", "-T", "api", "touch", "/app/prueba")
    # La base de datos no publica puertos en el host ("…:0" = sin publicar).
    assert not re.search(r":[1-9][0-9]*\s*$", compose("port", "db", "5432"))
    assert re.search(r":[1-9][0-9]*\s*$", compose("port", "web", "443"))
