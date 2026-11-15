"""Adaptador de Anthropic (Claude), sobre el SDK oficial."""

from __future__ import annotations

from collections.abc import Sequence

import anthropic
import httpx2
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

BASE_URL = "https://api.anthropic.com"

# Si los filtros de seguridad de estos modelos declinan una petición, la API la
# reintenta en otro modelo dentro de la misma llamada. Ese modelo se cobra a la
# clave del usuario, por eso se registra cuál respondió (`modelo_efectivo`).
_FALLBACK_BETA = "server-side-fallback-2026-07-01"
_MODELOS_CON_FALLBACK = frozenset({"claude-opus-5-5", "claude-sonnet-5-5"})

# Leer un documento escaneado no necesita razonamiento profundo; "medium"
# equilibra cuidado en la lectura con latencia (la petición es síncrona).
_EFFORT = "medium"


class AnthropicAdapter:
    id = "anthropic"

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
                "type": "image",
                "source": {"type": "base64", "media_type": "image/jpeg", "data": b64(page)},
            }
            for page in pages
        ]
        content.append({"type": "text", "text": USER_INSTRUCTION})
        request: dict[str, object] = {
            "model": model,
            "max_tokens": MAX_OUTPUT_TOKENS,
            "system": SYSTEM_PROMPT,
            "messages": [{"role": "user", "content": content}],
            "output_format": Extraccion,
            "output_config": {"effort": _EFFORT},
        }
        try:
            async with (
                http_client(timeout_s, transport) as http,
                anthropic.AsyncAnthropic(
                    api_key=api_key.get_secret_value(),
                    base_url=BASE_URL,
                    timeout=timeout_s,
                    max_retries=0,
                    http_client=http,
                ) as client,
            ):
                if model in _MODELOS_CON_FALLBACK:
                    message = await client.beta.messages.parse(
                        **request,  # type: ignore[arg-type]
                        betas=[_FALLBACK_BETA],
                        fallbacks="default",
                    )
                else:
                    message = await client.messages.parse(**request)  # type: ignore[arg-type]
        except anthropic.APIError as exc:
            raise _translate(exc) from None
        except ValidationError:
            raise errors.RespuestaInvalida(
                "La respuesta del modelo no tiene el formato esperado."
            ) from None

        request_id = getattr(message, "_request_id", None)
        # Antes de leer la salida: con estos motivos de parada puede no cumplir el esquema.
        if message.stop_reason == "refusal":
            raise errors.Rechazo(
                "El modelo declinó analizar este documento.", request_id=request_id
            )
        if message.stop_reason == "max_tokens":
            raise errors.RespuestaIncompleta(
                "El modelo no terminó su respuesta.", request_id=request_id
            )
        parsed = message.parsed_output
        if parsed is None:
            raise errors.RespuestaInvalida(
                "La respuesta del modelo no tiene el formato esperado.", request_id=request_id
            )
        return ExtractionOutcome(
            # Se revalida con nuestro esquema aunque el SDK ya lo haya hecho.
            extraccion=Extraccion.model_validate(parsed.model_dump()),
            tokens_entrada=message.usage.input_tokens,
            tokens_salida=message.usage.output_tokens,
            modelo_efectivo=message.model,
            request_id=request_id,
        )


def _translate(exc: anthropic.APIError) -> errors.ProviderError:
    """Convierte el error del SDK en uno propio, sin arrastrar la petición original."""
    if isinstance(exc, anthropic.APITimeoutError):
        return errors.TiempoAgotado("El proveedor tardó demasiado en responder.")
    if isinstance(exc, anthropic.APIConnectionError):
        return errors.ErrorConexion("No se pudo conectar con el proveedor.")
    if not isinstance(exc, anthropic.APIStatusError):
        return errors.ProveedorNoDisponible("El proveedor devolvió un error inesperado.")

    status = exc.status_code
    comunes = {"request_id": exc.request_id, "status": status}
    tipo = str(getattr(exc, "type", "") or "")
    if isinstance(exc, anthropic.AuthenticationError):
        return errors.ClaveInvalida("El proveedor rechazó la clave.", **comunes)
    if status == 402 or tipo == "billing_error":
        return errors.SinSaldo("La cuenta del proveedor no tiene saldo.", **comunes)
    if isinstance(exc, anthropic.PermissionDeniedError | anthropic.NotFoundError):
        return errors.SinAccesoModelo("La clave no tiene acceso a ese modelo.", **comunes)
    if isinstance(exc, anthropic.RateLimitError):
        return errors.LimiteProveedor(
            "El proveedor limitó las solicitudes de esta clave.",
            retry_after=retry_after_seconds(exc.response.headers),
            **comunes,
        )
    if status >= 500:
        return errors.ProveedorNoDisponible("El proveedor no está disponible.", **comunes)
    return errors.SolicitudRechazada("El proveedor rechazó la solicitud.", **comunes)
