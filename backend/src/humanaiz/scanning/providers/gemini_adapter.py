"""Adaptador de Google Gemini, sobre el SDK oficial `google-genai`."""

from __future__ import annotations

from collections.abc import Sequence

import httpx2
from google import genai
from google.genai import errors as genai_errors
from google.genai import types
from pydantic import SecretStr, ValidationError

from humanaiz.scanning import errors
from humanaiz.scanning.prompt import SYSTEM_PROMPT, USER_INSTRUCTION
from humanaiz.scanning.providers.base import MAX_OUTPUT_TOKENS, hardened_client_args
from humanaiz.scanning.types import Extraccion, ExtractionOutcome

BASE_URL = "https://generativelanguage.googleapis.com"

_PARADA_CORRECTA = "STOP"
_PARADA_POR_LIMITE = "MAX_TOKENS"
_PARADAS_DE_SEGURIDAD = frozenset(
    {"SAFETY", "RECITATION", "BLOCKLIST", "PROHIBITED_CONTENT", "SPII", "MODEL_ARMOR", "LANGUAGE"}
)


def _nombre(enum_o_texto: object) -> str:
    return str(getattr(enum_o_texto, "name", enum_o_texto) or "")


class GeminiAdapter:
    id = "gemini"

    async def extract(
        self,
        pages: Sequence[bytes],
        *,
        model: str,
        api_key: SecretStr,
        timeout_s: float,
        transport: httpx2.AsyncBaseTransport | None = None,
    ) -> ExtractionOutcome:
        client_args = hardened_client_args(timeout_s, transport)
        client_args.pop("timeout")  # el SDK fija el suyo desde HttpOptions.timeout (ms)
        client = genai.Client(
            # Explícito: sin esto, variables del entorno podrían activar Vertex AI.
            vertexai=False,
            api_key=api_key.get_secret_value(),
            http_options=types.HttpOptions(
                base_url=BASE_URL,
                timeout=int(timeout_s * 1000),
                retry_options=types.HttpRetryOptions(attempts=1),
                async_client_args=client_args,
            ),
        )
        contents: list[object] = [
            types.Part.from_bytes(data=page, mime_type="image/jpeg") for page in pages
        ]
        contents.append(USER_INSTRUCTION)
        try:
            response = await client.aio.models.generate_content(
                model=model,
                contents=contents,  # type: ignore[arg-type]
                config=types.GenerateContentConfig(
                    system_instruction=SYSTEM_PROMPT,
                    response_mime_type="application/json",
                    response_json_schema=Extraccion.model_json_schema(),
                    max_output_tokens=MAX_OUTPUT_TOKENS,
                ),
            )
        except genai_errors.APIError as exc:
            raise _translate(exc) from None
        except httpx2.TimeoutException:
            raise errors.TiempoAgotado("El proveedor tardó demasiado en responder.") from None
        except httpx2.TransportError:
            raise errors.ErrorConexion("No se pudo conectar con el proveedor.") from None
        finally:
            await client.aio.aclose()

        request_id = response.response_id
        bloqueo = getattr(response.prompt_feedback, "block_reason", None)
        if bloqueo:
            raise errors.Rechazo(
                "El modelo declinó analizar este documento.", request_id=request_id
            )
        candidatos = response.candidates or []
        parada = _nombre(candidatos[0].finish_reason) if candidatos else ""
        if parada in _PARADAS_DE_SEGURIDAD:
            raise errors.Rechazo(
                "El modelo declinó analizar este documento.", request_id=request_id
            )
        if parada == _PARADA_POR_LIMITE:
            raise errors.RespuestaIncompleta(
                "El modelo no terminó su respuesta.", request_id=request_id
            )
        texto = response.text if parada == _PARADA_CORRECTA else None
        if not texto:
            raise errors.RespuestaInvalida(
                "La respuesta del modelo no tiene el formato esperado.", request_id=request_id
            )
        try:
            extraccion = Extraccion.model_validate_json(texto)
        except ValidationError:
            raise errors.RespuestaInvalida(
                "La respuesta del modelo no tiene el formato esperado.", request_id=request_id
            ) from None
        usage = response.usage_metadata
        return ExtractionOutcome(
            extraccion=extraccion,
            tokens_entrada=usage.prompt_token_count if usage else None,
            tokens_salida=usage.candidates_token_count if usage else None,
            modelo_efectivo=response.model_version or model,
            request_id=request_id,
        )


def _translate(exc: genai_errors.APIError) -> errors.ProviderError:
    # Solo se usan el código y el estado: `str(exc)` incluye el cuerpo de la respuesta.
    status = int(getattr(exc, "code", 0) or 0)
    estado = str(getattr(exc, "status", "") or "")
    mensaje = str(getattr(exc, "message", "") or "").lower()
    comunes = {"status": status}
    clave_rechazada = "api key" in mensaje or "api_key" in mensaje
    if status == 401 or estado == "UNAUTHENTICATED" or (status in (400, 403) and clave_rechazada):
        return errors.ClaveInvalida("El proveedor rechazó la clave.", **comunes)
    if status in (403, 404) or estado in {"PERMISSION_DENIED", "NOT_FOUND"}:
        return errors.SinAccesoModelo("La clave no tiene acceso a ese modelo.", **comunes)
    if status == 429 or estado == "RESOURCE_EXHAUSTED":
        return errors.LimiteProveedor(
            "El proveedor limitó las solicitudes de esta clave.", **comunes
        )
    if status == 504 or estado == "DEADLINE_EXCEEDED":
        return errors.TiempoAgotado("El proveedor tardó demasiado en responder.", **comunes)
    if status >= 500:
        return errors.ProveedorNoDisponible("El proveedor no está disponible.", **comunes)
    return errors.SolicitudRechazada("El proveedor rechazó la solicitud.", **comunes)
