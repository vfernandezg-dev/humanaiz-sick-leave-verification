from __future__ import annotations

import json
from pathlib import Path

from humanaiz.main import create_app
from tests.conftest import SettingsFactory

CONTRATO = Path(__file__).resolve().parents[3] / "frontend" / "openapi.json"


def test_el_contrato_del_frontend_esta_al_dia(make_settings: SettingsFactory) -> None:
    """El frontend genera sus tipos desde `frontend/openapi.json`.

    Si la API cambia y este archivo no se regenera, los tipos del cliente
    mienten. Para actualizarlo:
        cd backend && uv run humanaiz export-openapi -o ../frontend/openapi.json
        cd ../frontend && pnpm gen:api
    """
    actual = create_app(make_settings()).openapi()
    guardado = json.loads(CONTRATO.read_text(encoding="utf-8"))
    assert guardado == json.loads(json.dumps(actual)), (
        "frontend/openapi.json no coincide con la API: regenera el contrato y los tipos."
    )


def test_la_clave_de_ia_no_aparece_en_ningun_esquema_de_respuesta(
    make_settings: SettingsFactory,
) -> None:
    esquema = create_app(make_settings()).openapi()
    texto = json.dumps(esquema["components"]["schemas"]).lower()
    for prohibido in ("api_key", "apikey", "llm_key", "clave_ia", "password_hash", "token_hash"):
        assert prohibido not in texto
