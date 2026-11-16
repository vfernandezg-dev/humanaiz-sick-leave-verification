"""Proveedores nuevos (OpenRouter, xAI, Mistral, Groq) y listado de modelos, sin red."""

from __future__ import annotations

import json
import logging
from typing import Any

import httpx2
import pytest
from pydantic import SecretStr, ValidationError

from humanaiz.scanning import errors
from humanaiz.scanning.catalog import get_provider
from humanaiz.scanning.engine import extract, listar_modelos
from humanaiz.scanning.types import Extraccion
from tests import files
from tests.unit.test_proveedores import CANARIO, EXTRACCION

PAGINA = files.jpeg_bytes(400, 300)


def chat_completion(texto: str, **cambios: Any) -> dict[str, Any]:
    cuerpo: dict[str, Any] = {
        "id": "gen-123",
        "object": "chat.completion",
        "created": 1,
        "model": "proveedor/modelo-real",
        "choices": [
            {
                "index": 0,
                "finish_reason": "stop",
                "message": {"role": "assistant", "content": texto},
            }
        ],
        "usage": {"prompt_tokens": 900, "completion_tokens": 120, "total_tokens": 1020},
    }
    return cuerpo | cambios


async def leer(proveedor: str, handler: Any, *, modelo: str = "a/b", paginas: int = 1):
    return await extract(
        [PAGINA] * paginas,
        provider=proveedor,
        model=modelo,
        api_key=SecretStr(CANARIO),
        timeout_s=20,
        transport=httpx2.MockTransport(handler),
    )


async def listar(proveedor: str, handler: Any):
    return await listar_modelos(
        provider=proveedor,
        api_key=SecretStr(CANARIO),
        timeout_s=20,
        transport=httpx2.MockTransport(handler),
    )


# ---------- catálogo ----------


@pytest.mark.parametrize(
    ("proveedor", "modelo", "valido"),
    [
        ("openrouter", "anthropic/claude-sonnet-5.5", True),
        ("openrouter", "google/gemini-3.8-flash:free", True),
        ("openrouter", "sin-autor", False),
        ("gemini", "gemini-3.8-flash", True),
        ("gemini", "gemma-4-27b-it", True),
        ("gemini", "gemini/../../v1beta/files", False),
        ("anthropic", "claude-opus-5-5", True),
        ("anthropic", "gpt-6-luna", False),
        ("openai", "ft:gpt-6-luna:mi-org::abc123", True),
        ("groq", "qwen/qwen3.8-27b", True),
        ("xai", "grok-4.7", True),
        ("mistral", "mistral-large-latest", True),
    ],
)
def test_patrones_de_modelo(proveedor: str, modelo: str, valido: bool) -> None:
    info = get_provider(proveedor)
    assert info is not None
    assert info.permite(info.normalizar_modelo(modelo)) is valido


def test_gemini_acepta_el_prefijo_models() -> None:
    info = get_provider("gemini")
    assert info is not None
    assert info.normalizar_modelo("models/gemini-3.8-flash") == "gemini-3.8-flash"


# ---------- interpretación flexible del modo JSON ----------


def test_json_flexible_admite_bloque_de_codigo_claves_extra_y_nulos_omitidos() -> None:
    datos = {k: v for k, v in EXTRACCION.items() if k not in {"citt", "fecha_emision_doc"}}
    datos["observaciones"] = "texto que no es del esquema"
    texto = "```json\n" + json.dumps(datos) + "\n```"
    extraccion = Extraccion.desde_json_flexible(texto)
    assert extraccion.citt is None and extraccion.fecha_emision_doc is None
    assert extraccion.dni_en_documento == "45678912"


@pytest.mark.parametrize(
    "texto",
    [
        "no es JSON",
        "[1, 2, 3]",
        json.dumps({"dni_en_documento": "1"}),  # faltan los obligatorios
        json.dumps(EXTRACCION | {"tipo_documento": "pasaporte"}),
        json.dumps(EXTRACCION | {"legible": "quizás"}),
    ],
)
def test_json_flexible_sigue_validando_lo_obligatorio(texto: str) -> None:
    with pytest.raises((ValidationError, ValueError)):
        Extraccion.desde_json_flexible(texto)


# ---------- lectura ----------


@pytest.mark.parametrize(
    ("proveedor", "host", "ruta"),
    [
        ("openrouter", "openrouter.ai", "/api/v1/chat/completions"),
        ("xai", "api.x.ai", "/v1/chat/completions"),
        ("mistral", "api.mistral.ai", "/v1/chat/completions"),
        ("groq", "api.groq.com", "/openai/v1/chat/completions"),
    ],
)
async def test_lectura_por_api_compatible(proveedor: str, host: str, ruta: str) -> None:
    vistas: list[httpx2.Request] = []

    def handler(request: httpx2.Request) -> httpx2.Response:
        vistas.append(request)
        return httpx2.Response(200, json=chat_completion(json.dumps(EXTRACCION)))

    resultado = await leer(proveedor, handler)
    assert resultado.extraccion.dni_en_documento == "45678912"
    assert (resultado.tokens_entrada, resultado.tokens_salida) == (900, 120)
    assert resultado.modelo_efectivo == "proveedor/modelo-real"

    [peticion] = vistas
    assert (peticion.url.scheme, peticion.url.host, peticion.url.path) == ("https", host, ruta)
    cuerpo = json.loads(peticion.content)
    assert cuerpo["response_format"] == {"type": "json_object"}
    assert [p["type"] for p in cuerpo["messages"][1]["content"]] == ["image_url", "text"]
    assert "JSON Schema" in cuerpo["messages"][0]["content"]
    # La clave solo en la cabecera de autorización.
    assert peticion.headers["authorization"] == f"Bearer {CANARIO}"
    assert CANARIO not in peticion.content.decode() and CANARIO not in str(peticion.url)
    # OpenRouter solo enruta a proveedores que respetan response_format.
    assert ("provider" in cuerpo) is (proveedor == "openrouter")


async def test_groq_rechaza_documentos_con_mas_paginas_de_las_que_admite() -> None:
    llamadas = 0

    def handler(request: httpx2.Request) -> httpx2.Response:
        nonlocal llamadas
        llamadas += 1
        return httpx2.Response(200, json=chat_completion(json.dumps(EXTRACCION)))

    with pytest.raises(errors.DocumentoNoSoportado):
        await leer("groq", handler, paginas=4)
    assert llamadas == 0  # no se llegó a gastar nada
    await leer("groq", handler, paginas=3)
    assert llamadas == 1


@pytest.mark.parametrize(
    ("cambios", "esperada"),
    [
        ({"choices": []}, errors.RespuestaInvalida),
        (
            {
                "choices": [
                    {
                        "index": 0,
                        "finish_reason": "length",
                        "message": {"role": "assistant", "content": "{"},
                    }
                ]
            },
            errors.RespuestaIncompleta,
        ),
        (
            {
                "choices": [
                    {
                        "index": 0,
                        "finish_reason": "content_filter",
                        "message": {"role": "assistant", "content": ""},
                    }
                ]
            },
            errors.Rechazo,
        ),
        (
            {
                "choices": [
                    {
                        "index": 0,
                        "finish_reason": "stop",
                        "message": {"role": "assistant", "content": None, "refusal": "No."},
                    }
                ]
            },
            errors.Rechazo,
        ),
        (
            {
                "choices": [
                    {
                        "index": 0,
                        "finish_reason": "stop",
                        "message": {"role": "assistant", "content": "Lo siento"},
                    }
                ]
            },
            errors.RespuestaInvalida,
        ),
    ],
)
async def test_respuestas_problematicas(cambios: dict[str, Any], esperada: type) -> None:
    def handler(request: httpx2.Request) -> httpx2.Response:
        return httpx2.Response(200, json=chat_completion("{}", **cambios))

    with pytest.raises(esperada):
        await leer("openrouter", handler)


@pytest.mark.parametrize(
    ("estado", "esperada"),
    [
        (401, errors.ClaveInvalida),
        (402, errors.SinSaldo),
        (404, errors.SinAccesoModelo),
        (429, errors.LimiteProveedor),
        (503, errors.ProveedorNoDisponible),
        (400, errors.SolicitudRechazada),
    ],
)
async def test_errores_de_apis_compatibles_sin_filtrar_la_clave(
    estado: int, esperada: type, caplog: pytest.LogCaptureFixture
) -> None:
    def handler(request: httpx2.Request) -> httpx2.Response:
        return httpx2.Response(
            estado, json={"error": {"message": f"clave {CANARIO} no válida", "code": estado}}
        )

    with caplog.at_level(logging.DEBUG), pytest.raises(esperada) as excinfo:
        await leer("openrouter", handler)
    exc = excinfo.value
    assert exc.__cause__ is None
    for texto in (str(exc), repr(vars(exc)), caplog.text):
        assert CANARIO not in texto


# ---------- listado de modelos (y validación de la clave) ----------


async def test_listado_openrouter_valida_la_clave_y_filtra_por_imagen() -> None:
    vistas: list[httpx2.Request] = []

    def handler(request: httpx2.Request) -> httpx2.Response:
        vistas.append(request)
        if request.url.path == "/api/v1/key":
            return httpx2.Response(200, json={"data": {"usage": 0}})
        return httpx2.Response(
            200,
            json={
                "data": [
                    {"id": "openai/gpt-6.1-sol", "name": "OpenAI: GPT-6.1 Sol"},
                    {"id": "anthropic/claude-sonnet-5.5", "name": "Anthropic: Claude Sonnet 5.5"},
                    {"nombre": "sin id"},
                ]
            },
        )

    modelos = await listar("openrouter", handler)
    assert [m.id for m in modelos] == ["anthropic/claude-sonnet-5.5", "openai/gpt-6.1-sol"]
    assert [r.url.path for r in vistas] == ["/api/v1/key", "/api/v1/models"]
    assert vistas[1].url.params["input_modalities"] == "image"
    assert vistas[1].url.params["supported_parameters"] == "response_format"
    assert all(r.headers["authorization"] == f"Bearer {CANARIO}" for r in vistas)


async def test_listado_openrouter_con_clave_invalida() -> None:
    def handler(request: httpx2.Request) -> httpx2.Response:
        return httpx2.Response(401, json={"error": {"message": "No auth credentials found"}})

    with pytest.raises(errors.ClaveInvalida):
        await listar("openrouter", handler)


async def test_listado_openai_descarta_modelos_que_no_leen_documentos() -> None:
    ids = [
        "gpt-6.1-sol",
        "gpt-6-luna",
        "o5-mini",
        "gpt-6-audio-preview",
        "gpt-6-realtime",
        "text-embedding-4-large",
        "dall-e-4",
        "whisper-2",
        "gpt-6-transcribe",
    ]

    def handler(request: httpx2.Request) -> httpx2.Response:
        assert request.url.host == "api.openai.com" and request.url.path == "/v1/models"
        return httpx2.Response(
            200,
            json={
                "object": "list",
                "data": [
                    {"id": i, "object": "model", "created": 1, "owned_by": "openai"} for i in ids
                ],
            },
        )

    modelos = await listar("openai", handler)
    assert [m.id for m in modelos] == ["gpt-6-luna", "gpt-6.1-sol", "o5-mini"]


async def test_listado_anthropic() -> None:
    def handler(request: httpx2.Request) -> httpx2.Response:
        assert request.url.path == "/v1/models"
        # La clave viaja en una sola cabecera, nunca en la URL.
        assert sum(CANARIO in v for v in request.headers.values()) == 1
        assert CANARIO not in str(request.url)
        return httpx2.Response(
            200,
            json={
                "data": [
                    {
                        "type": "model",
                        "id": "claude-opus-5-5",
                        "display_name": "Claude Opus 5.5",
                        "created_at": "2026-10-01T00:00:00Z",
                    }
                ],
                "has_more": False,
                "first_id": "claude-opus-5-5",
                "last_id": "claude-opus-5-5",
            },
        )

    modelos = await listar("anthropic", handler)
    assert [(m.id, m.nombre) for m in modelos] == [("claude-opus-5-5", "Claude Opus 5.5")]


async def test_listado_gemini_filtra_por_generacion_de_contenido() -> None:
    def handler(request: httpx2.Request) -> httpx2.Response:
        assert request.headers["x-goog-api-key"] == CANARIO
        return httpx2.Response(
            200,
            json={
                "models": [
                    {
                        "name": "models/gemini-3.8-flash",
                        "displayName": "Gemini 3.8 Flash",
                        "supportedGenerationMethods": ["generateContent", "countTokens"],
                    },
                    {
                        "name": "models/text-embedding-005",
                        "displayName": "Embedding",
                        "supportedGenerationMethods": ["embedContent"],
                    },
                    {
                        "name": "models/gemini-3.1-flash-image",
                        "displayName": "Imagen",
                        "supportedGenerationMethods": ["generateContent"],
                    },
                ]
            },
        )

    modelos = await listar("gemini", handler)
    assert [(m.id, m.nombre) for m in modelos] == [("gemini-3.8-flash", "Gemini 3.8 Flash")]


async def test_listado_de_api_compatible_generica() -> None:
    def handler(request: httpx2.Request) -> httpx2.Response:
        assert request.url.host == "api.groq.com" and request.url.path == "/openai/v1/models"
        return httpx2.Response(
            200,
            json={
                "object": "list",
                "data": [
                    {"id": i, "object": "model", "created": 1, "owned_by": "x"}
                    for i in ("qwen/qwen3.8-27b", "llama-5-8b")
                ],
            },
        )

    modelos = await listar("groq", handler)
    assert [m.id for m in modelos] == ["llama-5-8b", "qwen/qwen3.8-27b"]
