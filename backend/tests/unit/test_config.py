from __future__ import annotations

import pytest
from pydantic import ValidationError

from humanaiz.config import ConfigError, Settings, enforce_boot_guard, forbidden_env_present

BASE = {
    "database_url": "postgresql+asyncpg://u:p@localhost/db",
    "jwt_secret": "s" * 48,
}


def test_jwt_secret_corto_se_rechaza() -> None:
    with pytest.raises(ValidationError, match="JWT_SECRET"):
        Settings(**BASE | {"jwt_secret": "corto"})


@pytest.mark.parametrize(
    ("override", "mensaje"),
    [
        ({"public_origin": "http://sitio.example"}, "PUBLIC_ORIGIN"),
        ({"cookie_secure": False}, "COOKIE_SECURE"),
        ({"log_level": "debug"}, "LOG_LEVEL"),
        ({"enable_docs": True}, "ENABLE_DOCS"),
    ],
)
def test_produccion_exige_configuracion_segura(override: dict, mensaje: str) -> None:
    valores = BASE | {"environment": "production", "public_origin": "https://sitio.example"}
    with pytest.raises(ValidationError, match=mensaje):
        Settings(**valores | override)


def test_demo_exige_credenciales() -> None:
    with pytest.raises(ValidationError, match="DEMO_COLABORADOR_DNI"):
        Settings(**BASE | {"demo_mode": True})


def test_proveedores_desde_cadena(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LLM_ENABLED_PROVIDERS", "OpenAI, anthropic ,")
    assert Settings(**BASE).llm_enabled_providers == ("openai", "anthropic")


def test_cookie_host_solo_con_https() -> None:
    assert Settings(**BASE).session_cookie_name == "__Host-hz_session"
    assert Settings(**BASE | {"cookie_secure": False}).session_cookie_name == "hz_session"


def test_variables_prohibidas_detectadas() -> None:
    assert forbidden_env_present({"OPENAI_API_KEY": "x", "https_proxy": "y", "PATH": "z"}) == [
        "OPENAI_API_KEY",
        "HTTPS_PROXY",
    ]
    assert forbidden_env_present({"OPENAI_API_KEY": ""}) == []


def test_guardia_de_arranque_bloquea_en_produccion(monkeypatch: pytest.MonkeyPatch) -> None:
    for nombre in ("OPENAI_API_KEY", "ANTHROPIC_API_KEY", "HTTPS_PROXY", "HTTP_PROXY"):
        monkeypatch.delenv(nombre, raising=False)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-no-deberia-estar")
    produccion = Settings(
        **BASE | {"environment": "production", "public_origin": "https://sitio.example"}
    )
    with pytest.raises(ConfigError, match="ANTHROPIC_API_KEY"):
        enforce_boot_guard(produccion)
    # Fuera de producción solo se informa.
    assert "ANTHROPIC_API_KEY" in enforce_boot_guard(Settings(**BASE))
