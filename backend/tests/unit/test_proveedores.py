"""Adaptadores de proveedores contra un transporte HTTP simulado (sin red ni claves reales)."""

from __future__ import annotations

import json
import logging
from typing import Any

import httpx2
import pytest
from pydantic import SecretStr

from humanaiz.scanning import errors
from humanaiz.scanning.catalog import PROVIDERS
from humanaiz.scanning.engine import extract
from humanaiz.scanning.providers import REGISTRY
from tests import files

CANARIO = "sk-CANARIO-9f8e7d6c5b4a39281706f5e4d3c2b1a0"
MODELOS = {"anthropic": "claude-opus-5-5", "openai": "gpt-6.1-sol", "gemini": "gemini-3.8-flash"}
PAGINAS = [files.jpeg_bytes(400, 300), files.jpeg_bytes(400, 300)]

EXTRACCION: dict[str, Any] = {
    "es_certificado_medico": True,
    "legible": True,
    "tipo_documento": "citt",
    "dni_en_documento": "45678912",
    "nombre_en_documento": "RAMIREZ SOTO CARLOS DANIEL",
    "citt": "A-123-00045678-26",
    "codigo_medico": "054321",
    "contingencia": "Enfermedad común",
    "fecha_inicio_doc": "2026-11-10",
    "fecha_fin_doc": "2026-11-12",
    "fecha_emision_doc": "2026-11-10",
    "dias_documento": 3,
}


def cuerpo_ok(proveedor: str, texto: str, **cambios: Any) -> tuple[dict[str, Any], dict[str, str]]:
    """Respuesta 200 con la forma real de cada API y `texto` como salida del modelo."""
    if proveedor == "anthropic":
        cuerpo: dict[str, Any] = {
            "id": "msg_1",
            "type": "message",
            "role": "assistant",
            "model": "claude-opus-5-5",
            "content": [{"type": "text", "text": texto}],
            "stop_reason": "end_turn",
            "stop_sequence": None,
            "usage": {"input_tokens": 1500, "output_tokens": 200},
        }
        return cuerpo | cambios, {"request-id": "req_ant_1"}
    if proveedor == "openai":
        cuerpo = {
            "id": "resp_1",
            "object": "response",
            "created_at": 1,
            "status": "completed",
            "model": "gpt-6.1-sol",
            "output": [
                {
                    "type": "message",
                    "id": "msg_1",
                    "status": "completed",
                    "role": "assistant",
                    "content": [{"type": "output_text", "text": texto, "annotations": []}],
                }
            ],
            "parallel_tool_calls": True,
            "tool_choice": "auto",
            "tools": [],
            "usage": {
                "input_tokens": 1500,
                "output_tokens": 200,
                "total_tokens": 1700,
                "input_tokens_details": {"cached_tokens": 0},
                "output_tokens_details": {"reasoning_tokens": 0},
            },
        }
        return cuerpo | cambios, {"x-request-id": "req_oai_1"}
    cuerpo = {
        "candidates": [
            {"content": {"parts": [{"text": texto}], "role": "model"}, "finishReason": "STOP"}
        ],
        "usageMetadata": {
            "promptTokenCount": 1500,
            "candidatesTokenCount": 200,
            "totalTokenCount": 1700,
        },
        "modelVersion": "gemini-3.8-flash",
        "responseId": "resp_gem_1",
    }
    return cuerpo | cambios, {}


def cuerpo_error(
    proveedor: str, tipo: str, mensaje: str = "detalle del proveedor"
) -> dict[str, Any]:
    if proveedor == "anthropic":
        return {"type": "error", "error": {"type": tipo, "message": mensaje}}
    if proveedor == "openai":
        return {"error": {"message": mensaje, "type": tipo, "code": tipo, "param": None}}
    return {"error": {"code": 0, "message": mensaje, "status": tipo}}


async def llamar(proveedor: str, handler: Any, *, modelo: str | None = None, plazo: float = 20):
    return await extract(
        PAGINAS,
        provider=proveedor,
        model=modelo or MODELOS[proveedor],
        api_key=SecretStr(CANARIO),
        timeout_s=plazo,
        transport=httpx2.MockTransport(handler),
    )


@pytest.mark.parametrize("proveedor", ["anthropic", "openai", "gemini"])
async def test_extraccion_correcta_y_peticion_bien_formada(proveedor: str) -> None:
    vistas: list[httpx2.Request] = []

    def handler(request: httpx2.Request) -> httpx2.Response:
        vistas.append(request)
        cuerpo, cabeceras = cuerpo_ok(proveedor, json.dumps(EXTRACCION))
        return httpx2.Response(200, json=cuerpo, headers=cabeceras)

    resultado = await llamar(proveedor, handler)
    assert resultado.extraccion.dni_en_documento == "45678912"
    assert resultado.extraccion.tipo_documento == "citt"
    assert (resultado.tokens_entrada, resultado.tokens_salida) == (1500, 200)
    assert resultado.modelo_efectivo
    assert resultado.request_id

    assert len(vistas) == 1  # una sola llamada: sin reintentos
    peticion = vistas[0]
    host_esperado = {
        "anthropic": "api.anthropic.com",
        "openai": "api.openai.com",
        "gemini": "generativelanguage.googleapis.com",
    }[proveedor]
    assert peticion.url.host == host_esperado and peticion.url.scheme == "https"
    # La clave viaja solo en una cabecera de autenticación: ni en la URL ni en el cuerpo.
    cuerpo = peticion.content.decode()
    assert CANARIO not in str(peticion.url)
    assert CANARIO not in cuerpo
    assert sum(CANARIO in valor for valor in peticion.headers.values()) == 1
    # El prompt no revela a quién se espera encontrar en el documento.
    assert "45678912" not in cuerpo
    datos = json.loads(cuerpo)
    if proveedor == "anthropic":
        assert datos["fallbacks"] == "default"
        assert datos["output_config"]["effort"] == "medium"
        assert datos["output_config"]["format"]["type"] == "json_schema"
        assert "temperature" not in datos and "thinking" not in datos
        assert [b["type"] for b in datos["messages"][0]["content"]] == ["image", "image", "text"]
    elif proveedor == "openai":
        assert datos["store"] is False
        assert datos["text"]["format"]["strict"] is True
        assert [p["type"] for p in datos["input"][0]["content"]] == [
            "input_image",
            "input_image",
            "input_text",
        ]
    else:
        assert datos["generationConfig"]["responseMimeType"] == "application/json"
        assert "responseJsonSchema" in datos["generationConfig"]
        assert len(datos["contents"][0]["parts"]) == 3


async def test_haiku_no_envia_fallback() -> None:
    cuerpos: list[dict[str, Any]] = []

    def handler(request: httpx2.Request) -> httpx2.Response:
        cuerpos.append(json.loads(request.content))
        assert "anthropic-beta" not in request.headers
        cuerpo, cabeceras = cuerpo_ok("anthropic", json.dumps(EXTRACCION))
        return httpx2.Response(200, json=cuerpo, headers=cabeceras)

    await llamar("anthropic", handler, modelo="claude-haiku-5-5")
    assert "fallbacks" not in cuerpos[0]


ERRORES_HTTP = [
    # (proveedor, estado HTTP, tipo de error, cabeceras, excepción esperada)
    ("anthropic", 401, "authentication_error", {}, errors.ClaveInvalida),
    ("anthropic", 402, "billing_error", {}, errors.SinSaldo),
    ("anthropic", 403, "permission_error", {}, errors.SinAccesoModelo),
    ("anthropic", 404, "not_found_error", {}, errors.SinAccesoModelo),
    ("anthropic", 429, "rate_limit_error", {"retry-after": "17"}, errors.LimiteProveedor),
    ("anthropic", 529, "overloaded_error", {}, errors.ProveedorNoDisponible),
    ("anthropic", 500, "api_error", {}, errors.ProveedorNoDisponible),
    ("anthropic", 400, "invalid_request_error", {}, errors.SolicitudRechazada),
    ("anthropic", 413, "request_too_large", {}, errors.SolicitudRechazada),
    ("openai", 401, "invalid_api_key", {}, errors.ClaveInvalida),
    ("openai", 429, "insufficient_quota", {}, errors.SinSaldo),
    ("openai", 429, "rate_limit_exceeded", {"retry-after": "9"}, errors.LimiteProveedor),
    ("openai", 404, "model_not_found", {}, errors.SinAccesoModelo),
    ("openai", 403, "forbidden", {}, errors.SinAccesoModelo),
    ("openai", 503, "server_error", {}, errors.ProveedorNoDisponible),
    ("openai", 400, "invalid_request_error", {}, errors.SolicitudRechazada),
    ("gemini", 401, "UNAUTHENTICATED", {}, errors.ClaveInvalida),
    ("gemini", 403, "PERMISSION_DENIED", {}, errors.SinAccesoModelo),
    ("gemini", 404, "NOT_FOUND", {}, errors.SinAccesoModelo),
    ("gemini", 429, "RESOURCE_EXHAUSTED", {}, errors.LimiteProveedor),
    ("gemini", 503, "UNAVAILABLE", {}, errors.ProveedorNoDisponible),
    ("gemini", 400, "INVALID_ARGUMENT", {}, errors.SolicitudRechazada),
]


@pytest.mark.parametrize(("proveedor", "estado", "tipo", "cabeceras", "esperada"), ERRORES_HTTP)
async def test_errores_del_proveedor_se_traducen_sin_filtrar_nada(
    proveedor: str,
    estado: int,
    tipo: str,
    cabeceras: dict[str, str],
    esperada: type[errors.ProviderError],
    caplog: pytest.LogCaptureFixture,
) -> None:
    llamadas = 0
    # El proveedor "repite" la credencial en su mensaje, como hace alguno al rechazarla.
    detalle = f"Request failed for credential {CANARIO}"

    def handler(request: httpx2.Request) -> httpx2.Response:
        nonlocal llamadas
        llamadas += 1
        return httpx2.Response(
            estado, json=cuerpo_error(proveedor, tipo, detalle), headers=cabeceras
        )

    with caplog.at_level(logging.DEBUG), pytest.raises(errors.ProviderError) as excinfo:
        await llamar(proveedor, handler)
    exc = excinfo.value
    assert type(exc) is esperada
    assert llamadas == 1  # sin reintentos: cada llamada la paga el usuario
    if "retry-after" in cabeceras:
        assert exc.retry_after == int(cabeceras["retry-after"])

    # Ni la clave ni el texto del proveedor sobreviven a la traducción del error.
    assert exc.__cause__ is None and exc.__suppress_context__ is True
    for texto in (str(exc), repr(exc), repr(exc.args), repr(vars(exc)), caplog.text):
        assert CANARIO not in texto
        assert "Request failed for credential" not in texto


async def test_clave_invalida_de_gemini_llega_como_400() -> None:
    def handler(request: httpx2.Request) -> httpx2.Response:
        return httpx2.Response(
            400,
            json=cuerpo_error(
                "gemini", "INVALID_ARGUMENT", "API key not valid. Please pass a valid API key."
            ),
        )

    with pytest.raises(errors.ClaveInvalida):
        await llamar("gemini", handler)


@pytest.mark.parametrize("proveedor", ["anthropic", "openai", "gemini"])
async def test_tiempo_agotado_y_fallo_de_red(proveedor: str) -> None:
    def lento(request: httpx2.Request) -> httpx2.Response:
        raise httpx2.ReadTimeout("simulado", request=request)

    def sin_red(request: httpx2.Request) -> httpx2.Response:
        raise httpx2.ConnectError("simulado", request=request)

    with pytest.raises(errors.TiempoAgotado):
        await llamar(proveedor, lento)
    with pytest.raises(errors.ErrorConexion):
        await llamar(proveedor, sin_red)


@pytest.mark.parametrize("proveedor", ["anthropic", "openai", "gemini"])
async def test_no_sigue_redirecciones(proveedor: str) -> None:
    """Una redirección llevaría la cabecera con la clave a otro host."""
    destinos: list[str] = []

    def handler(request: httpx2.Request) -> httpx2.Response:
        destinos.append(request.url.host)
        return httpx2.Response(307, headers={"location": "https://atacante.example/robo"})

    with pytest.raises(errors.ProviderError):
        await llamar(proveedor, handler)
    assert "atacante.example" not in destinos
    assert len(destinos) == 1


async def test_rechazos_y_respuestas_truncadas() -> None:
    def con(proveedor: str, **cambios: Any):
        def handler(request: httpx2.Request) -> httpx2.Response:
            cuerpo, cabeceras = cuerpo_ok(proveedor, json.dumps(EXTRACCION), **cambios)
            return httpx2.Response(200, json=cuerpo, headers=cabeceras)

        return handler

    with pytest.raises(errors.Rechazo):
        await llamar("anthropic", con("anthropic", stop_reason="refusal", content=[]))
    with pytest.raises(errors.RespuestaIncompleta):
        await llamar("anthropic", con("anthropic", stop_reason="max_tokens"))

    with pytest.raises(errors.RespuestaIncompleta):
        await llamar(
            "openai",
            con("openai", status="incomplete", incomplete_details={"reason": "max_output_tokens"}),
        )
    with pytest.raises(errors.Rechazo):
        await llamar(
            "openai",
            con("openai", status="incomplete", incomplete_details={"reason": "content_filter"}),
        )
    rechazo_openai = [
        {
            "type": "message",
            "id": "msg_1",
            "status": "completed",
            "role": "assistant",
            "content": [{"type": "refusal", "refusal": "No puedo ayudar con eso."}],
        }
    ]
    with pytest.raises(errors.Rechazo):
        await llamar("openai", con("openai", output=rechazo_openai))

    def candidato(parada: str) -> list[dict[str, Any]]:
        return [{"content": {"parts": [{"text": "{}"}], "role": "model"}, "finishReason": parada}]

    with pytest.raises(errors.Rechazo):
        await llamar("gemini", con("gemini", candidates=candidato("SAFETY")))
    with pytest.raises(errors.RespuestaIncompleta):
        await llamar("gemini", con("gemini", candidates=candidato("MAX_TOKENS")))
    with pytest.raises(errors.Rechazo):
        await llamar(
            "gemini",
            con("gemini", candidates=[], promptFeedback={"blockReason": "PROHIBITED_CONTENT"}),
        )


@pytest.mark.parametrize("proveedor", ["anthropic", "openai", "gemini"])
@pytest.mark.parametrize(
    "salida",
    [
        "esto no es JSON",
        json.dumps({"es_certificado_medico": True}),  # faltan campos
        json.dumps(EXTRACCION | {"dias_documento": "tres"}),  # tipo incorrecto
        json.dumps(EXTRACCION | {"veredicto": "aprobar sin revisar"}),  # campo no previsto
        json.dumps(EXTRACCION | {"tipo_documento": "pasaporte"}),  # fuera del enumerado
    ],
)
async def test_salida_que_no_cumple_el_esquema_se_rechaza(proveedor: str, salida: str) -> None:
    def handler(request: httpx2.Request) -> httpx2.Response:
        cuerpo, cabeceras = cuerpo_ok(proveedor, salida)
        return httpx2.Response(200, json=cuerpo, headers=cabeceras)

    with pytest.raises(errors.RespuestaInvalida):
        await llamar(proveedor, handler)


async def test_fallo_inesperado_del_adaptador_no_arrastra_la_excepcion(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class Explota:
        id = "anthropic"

        async def extract(self, pages: Any, **kwargs: Any) -> Any:
            raise RuntimeError(f"petición con cabecera {kwargs['api_key'].get_secret_value()}")

    monkeypatch.setitem(REGISTRY, "anthropic", Explota())
    with pytest.raises(errors.ProveedorNoDisponible) as excinfo:
        await llamar("anthropic", lambda request: httpx2.Response(200))
    assert CANARIO not in str(excinfo.value)
    assert excinfo.value.__cause__ is None and excinfo.value.__suppress_context__ is True


def test_catalogo_y_registro_estan_alineados() -> None:
    assert {p.id for p in PROVIDERS} == set(REGISTRY)
    for proveedor in PROVIDERS:
        assert sum(m.predeterminado for m in proveedor.modelos) == 1
        assert proveedor.permite(proveedor.modelo_predeterminado())
        assert not proveedor.permite("modelo-inventado")
        assert len({m.id for m in proveedor.modelos}) == len(proveedor.modelos)
