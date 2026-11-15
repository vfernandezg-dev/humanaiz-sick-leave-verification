"""Contrato común de los adaptadores de proveedores de IA.

Reglas que todo adaptador cumple, porque maneja la clave del usuario:
1. El cliente del SDK se construye dentro de la llamada y se cierra al salir:
   no hay caché de clientes ni de claves.
2. `api_key` y `base_url` van siempre explícitos; nada se toma del entorno.
3. Sin reintentos automáticos: cada llamada la paga el usuario.
4. El cliente HTTP no sigue redirecciones ni usa proxies del entorno.
5. Las excepciones del SDK (que llevan la petición, con sus cabeceras) no
   salen del adaptador: se traducen a un `ProviderError` propio con
   `raise ... from None`.
"""

from __future__ import annotations

import base64
from collections.abc import Sequence
from typing import Protocol

import httpx2
from pydantic import SecretStr

from humanaiz.scanning.types import ExtractionOutcome

MAX_OUTPUT_TOKENS = 16_000
_CONNECT_TIMEOUT_S = 10.0


class ProviderAdapter(Protocol):
    id: str

    async def extract(
        self,
        pages: Sequence[bytes],
        *,
        model: str,
        api_key: SecretStr,
        timeout_s: float,
        transport: httpx2.AsyncBaseTransport | None = None,
    ) -> ExtractionOutcome:
        """Envía las páginas (JPEG) y devuelve la extracción validada.

        `transport` solo se usa en pruebas, para simular al proveedor.
        """
        ...


def hardened_client_args(
    timeout_s: float, transport: httpx2.AsyncBaseTransport | None
) -> dict[str, object]:
    args: dict[str, object] = {
        "timeout": httpx2.Timeout(timeout_s, connect=min(_CONNECT_TIMEOUT_S, timeout_s)),
        # Las cabeceras con la clave no deben viajar a otro host por una redirección.
        "follow_redirects": False,
        # Ignora HTTPS_PROXY, SSL_CERT_FILE y similares.
        "trust_env": False,
    }
    if transport is not None:
        args["transport"] = transport
    return args


def http_client(
    timeout_s: float, transport: httpx2.AsyncBaseTransport | None = None
) -> httpx2.AsyncClient:
    return httpx2.AsyncClient(**hardened_client_args(timeout_s, transport))  # type: ignore[arg-type]


def b64(page: bytes) -> str:
    return base64.standard_b64encode(page).decode("ascii")


def retry_after_seconds(headers: object) -> int | None:
    """Lee Retry-After (en segundos) de unas cabeceras de respuesta, si es un entero."""
    try:
        value = headers.get("retry-after")  # type: ignore[attr-defined]
        return max(1, int(float(value))) if value else None
    except (AttributeError, TypeError, ValueError):
        return None
