"""Adaptador de OpenAI (Responses API), sobre el SDK oficial."""

from __future__ import annotations

from collections.abc import Sequence

import httpx2
import openai
from pydantic import SecretStr, ValidationError

from humanaiz.scanning import errors
from humanaiz.scanning.prompt import SYSTEM_PROMPT, USER_INSTRUCTION
from humanaiz.scanning.providers.base import (
    MAX_OUTPUT_TOKENS,
    b64,
    http_client,
    retry_after_seconds,
)
from humanaiz.scanning.types import Extraccion, ExtractionOutcome

BASE_URL = "https://api.openai.com/v1"


class OpenAIAdapter:
    id = "openai"

    async def extract(
        self,
        pages: Sequence[bytes],
        *,
        model: str,
        api_key: SecretStr,
        timeout_s: float,
        transport: httpx2.AsyncBaseTransport | None = None,
    ) -> ExtractionOutcome:
        content: list[dict[str, object]] = [
            {
                "type": "input_image",
                "image_url": f"data:image/jpeg;base64,{b64(page)}",
                "detail": "high",
            }
            for page in pages
        ]
        content.append({"type": "input_text", "text": USER_INSTRUCTION})
        try:
            async with (
                http_client(timeout_s, transport) as http,
                openai.AsyncOpenAI(
                    api_key=api_key.get_secret_value(),
                    base_url=BASE_URL,
                    timeout=timeout_s,
                    max_retries=0,
                    http_client=http,
                ) as client,
            ):
                response = await client.responses.parse(
                    model=model,
                    instructions=SYSTEM_PROMPT,
                    input=[{"role": "user", "content": content}],  # type: ignore[list-item]
                    text_format=Extraccion,
                    max_output_tokens=MAX_OUTPUT_TOKENS,
                    # El proveedor no conserva la respuesta: es un documento médico.
                    store=False,
                )
        except openai.LengthFinishReasonError:
            raise errors.RespuestaIncompleta("El modelo no terminó su respuesta.") from None
        except openai.ContentFilterFinishReasonError:
            raise errors.Rechazo("El modelo declinó analizar este documento.") from None
        except openai.APIError as exc:
            raise _translate(exc) from None
        except ValidationError:
            raise errors.RespuestaInvalida(
                "La respuesta del modelo no tiene el formato esperado."
            ) from None

        request_id = getattr(response, "_request_id", None)
        if response.status == "incomplete":
            motivo = getattr(response.incomplete_details, "reason", None)
            if motivo == "content_filter":
                raise errors.Rechazo(
                    "El modelo declinó analizar este documento.", request_id=request_id
                )
            raise errors.RespuestaIncompleta(
                "El modelo no terminó su respuesta.", request_id=request_id
            )
        if _refused(response):
            raise errors.Rechazo(
                "El modelo declinó analizar este documento.", request_id=request_id
            )
        parsed = response.output_parsed
        if parsed is None:
            raise errors.RespuestaInvalida(
                "La respuesta del modelo no tiene el formato esperado.", request_id=request_id
            )
        usage = response.usage
        return ExtractionOutcome(
            extraccion=Extraccion.model_validate(parsed.model_dump()),
            tokens_entrada=usage.input_tokens if usage else None,
            tokens_salida=usage.output_tokens if usage else None,
            modelo_efectivo=response.model,
            request_id=request_id,
        )


def _refused(response: object) -> bool:
    for item in getattr(response, "output", None) or ():
        for part in getattr(item, "content", None) or ():
            if getattr(part, "type", None) == "refusal":
                return True
    return False


def _translate(exc: openai.APIError) -> errors.ProviderError:
    if isinstance(exc, openai.APITimeoutError):
        return errors.TiempoAgotado("El proveedor tardó demasiado en responder.")
    if isinstance(exc, openai.APIConnectionError):
        return errors.ErrorConexion("No se pudo conectar con el proveedor.")
    if not isinstance(exc, openai.APIStatusError):
        return errors.ProveedorNoDisponible("El proveedor devolvió un error inesperado.")

    status = exc.status_code
    codigo = str(getattr(exc, "code", "") or "")
    comunes = {"request_id": exc.request_id, "status": status}
    if isinstance(exc, openai.AuthenticationError):
        return errors.ClaveInvalida("El proveedor rechazó la clave.", **comunes)
    if codigo in {"insufficient_quota", "billing_hard_limit_reached"}:
        return errors.SinSaldo("La cuenta del proveedor no tiene saldo.", **comunes)
    if isinstance(exc, openai.PermissionDeniedError | openai.NotFoundError) or codigo in {
        "model_not_found",
        "unsupported_model",
    }:
        return errors.SinAccesoModelo("La clave no tiene acceso a ese modelo.", **comunes)
    if isinstance(exc, openai.RateLimitError):
        return errors.LimiteProveedor(
            "El proveedor limitó las solicitudes de esta clave.",
            retry_after=retry_after_seconds(exc.response.headers),
            **comunes,
        )
    if status >= 500:
        return errors.ProveedorNoDisponible("El proveedor no está disponible.", **comunes)
    return errors.SolicitudRechazada("El proveedor rechazó la solicitud.", **comunes)
