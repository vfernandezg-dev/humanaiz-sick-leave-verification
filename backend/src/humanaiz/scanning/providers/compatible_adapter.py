"""Adaptador para APIs compatibles con la de OpenAI (Chat Completions).

Sirve a OpenRouter, xAI, Mistral y Groq: misma forma de petición, otra URL
base (fija en el catálogo, nunca elegida por el usuario). No todas garantizan
salida con esquema estricto, así que se usa el "modo JSON", se incluye el
esquema en las instrucciones y la respuesta se valida igual con Pydantic.
"""

from __future__ import annotations

from collections.abc import Sequence

import httpx2
import openai
from pydantic import SecretStr, ValidationError

from humanaiz.scanning import errors
from humanaiz.scanning.prompt import SYSTEM_PROMPT, USER_INSTRUCTION, instruccion_json
from humanaiz.scanning.providers.base import (
    MAX_MODELOS_LISTADOS,
    b64,
    hardened_client_args,
    http_client,
)
from humanaiz.scanning.providers.openai_adapter import listar_ids_compatibles, traducir_error
from humanaiz.scanning.types import Extraccion, ExtractionOutcome, ModeloDisponible

# La salida es un objeto pequeño; algunos proveedores rechazan topes altos.
_MAX_TOKENS = 4096


class CompatibleAdapter:
    def __init__(self, id: str, base_url: str, *, max_imagenes: int = 20) -> None:
        self.id = id
        self.base_url = base_url
        self.max_imagenes = max_imagenes

    def _extra_body(self) -> dict[str, object] | None:
        if self.id == "openrouter":
            # Solo enrutar a proveedores que admitan response_format.
            return {"provider": {"require_parameters": True}}
        return None

    async def extract(
        self,
        pages: Sequence[bytes],
        *,
        model: str,
        api_key: SecretStr,
        timeout_s: float,
        transport: httpx2.AsyncBaseTransport | None = None,
    ) -> ExtractionOutcome:
        if len(pages) > self.max_imagenes:
            raise errors.DocumentoNoSoportado(
                f"Este proveedor admite hasta {self.max_imagenes} páginas por lectura."
            )
        content: list[dict[str, object]] = [
            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64(page)}"}}
            for page in pages
        ]
        content.append({"type": "text", "text": USER_INSTRUCTION})
        try:
            async with (
                http_client(timeout_s, transport) as http,
                openai.AsyncOpenAI(
                    api_key=api_key.get_secret_value(),
                    base_url=self.base_url,
                    timeout=timeout_s,
                    max_retries=0,
                    http_client=http,
                ) as client,
            ):
                response = await client.chat.completions.create(
                    model=model,
                    messages=[
                        {"role": "system", "content": f"{SYSTEM_PROMPT}\n{instruccion_json()}"},
                        {"role": "user", "content": content},  # type: ignore[typeddict-item]
                    ],
                    response_format={"type": "json_object"},
                    max_tokens=_MAX_TOKENS,
                    extra_body=self._extra_body(),
                )
        except openai.APIError as exc:
            raise traducir_error(exc) from None

        request_id = getattr(response, "_request_id", None) or getattr(response, "id", None)
        if not response.choices:
            raise errors.RespuestaInvalida(
                "La respuesta del modelo no tiene el formato esperado.", request_id=request_id
            )
        choice = response.choices[0]
        if choice.finish_reason == "content_filter" or getattr(choice.message, "refusal", None):
            raise errors.Rechazo(
                "El modelo declinó analizar este documento.", request_id=request_id
            )
        if choice.finish_reason == "length":
            raise errors.RespuestaIncompleta(
                "El modelo no terminó su respuesta.", request_id=request_id
            )
        try:
            extraccion = Extraccion.desde_json_flexible(choice.message.content or "")
        except (ValidationError, ValueError):
            raise errors.RespuestaInvalida(
                "La respuesta del modelo no tiene el formato esperado.", request_id=request_id
            ) from None
        usage = response.usage
        return ExtractionOutcome(
            extraccion=extraccion,
            tokens_entrada=usage.prompt_tokens if usage else None,
            tokens_salida=usage.completion_tokens if usage else None,
            modelo_efectivo=response.model or model,
            request_id=str(request_id)[:100] if request_id else None,
        )

    async def listar_modelos(
        self,
        *,
        api_key: SecretStr,
        timeout_s: float,
        transport: httpx2.AsyncBaseTransport | None = None,
    ) -> list[ModeloDisponible]:
        if self.id == "openrouter":
            return await self._listar_openrouter(api_key, timeout_s, transport)
        ids = await listar_ids_compatibles(self.base_url, api_key, timeout_s, transport)
        return [ModeloDisponible(id=i, nombre=i) for i in ids]

    async def _listar_openrouter(
        self, api_key: SecretStr, timeout_s: float, transport: httpx2.AsyncBaseTransport | None
    ) -> list[ModeloDisponible]:
        # El catálogo de OpenRouter es común a todas las cuentas: primero se valida
        # la clave con /key y luego se piden solo los modelos que leen imágenes y
        # admiten response_format.
        cabeceras = {"Authorization": f"Bearer {api_key.get_secret_value()}"}
        try:
            async with httpx2.AsyncClient(
                **hardened_client_args(timeout_s, transport)  # type: ignore[arg-type]
            ) as http:
                clave = await http.get(f"{self.base_url}/key", headers=cabeceras)
                _comprobar_estado(clave)
                respuesta = await http.get(
                    f"{self.base_url}/models",
                    headers=cabeceras,
                    params={"input_modalities": "image", "supported_parameters": "response_format"},
                )
                _comprobar_estado(respuesta)
                datos = respuesta.json().get("data", [])
        except httpx2.TimeoutException:
            raise errors.TiempoAgotado("El proveedor tardó demasiado en responder.") from None
        except httpx2.TransportError:
            raise errors.ErrorConexion("No se pudo conectar con el proveedor.") from None
        except ValueError:
            raise errors.RespuestaInvalida(
                "El proveedor devolvió una respuesta inesperada."
            ) from None
        modelos = [
            ModeloDisponible(id=str(m["id"]), nombre=str(m.get("name") or m["id"]))
            for m in datos
            if isinstance(m, dict) and isinstance(m.get("id"), str)
        ]
        return sorted(modelos, key=lambda m: m.id)[:MAX_MODELOS_LISTADOS]


def _comprobar_estado(respuesta: httpx2.Response) -> None:
    """Traduce un estado HTTP de error sin conservar la petición ni el cuerpo."""
    estado = respuesta.status_code
    if estado < 400:
        return
    comunes = {"status": estado}
    if estado == 401:
        raise errors.ClaveInvalida("El proveedor rechazó la clave.", **comunes)
    if estado == 402:
        raise errors.SinSaldo("La cuenta del proveedor no tiene saldo.", **comunes)
    if estado == 403:
        raise errors.SinAccesoModelo("La clave no tiene permisos suficientes.", **comunes)
    if estado == 429:
        raise errors.LimiteProveedor(
            "El proveedor limitó las solicitudes de esta clave.", **comunes
        )
    if estado >= 500:
        raise errors.ProveedorNoDisponible("El proveedor no está disponible.", **comunes)
    raise errors.SolicitudRechazada("El proveedor rechazó la solicitud.", **comunes)
