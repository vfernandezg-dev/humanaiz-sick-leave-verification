"""Punto de entrada del motor: extracción (con red) y evaluación (pura).

`humanaiz.scanning.__init__` queda vacío a propósito: el proceso hijo que
decodifica archivos no confiables importa ese paquete y no debe cargar los SDK
de los proveedores.
"""

from __future__ import annotations

import logging
from collections.abc import Sequence

import httpx2
from pydantic import SecretStr

from humanaiz.scanning.errors import ProveedorNoDisponible, ScanningError
from humanaiz.scanning.providers import get_adapter
from humanaiz.scanning.rules import evaluate
from humanaiz.scanning.types import ExtractionOutcome

logger = logging.getLogger(__name__)

__all__ = ["evaluate", "extract"]


async def extract(
    pages: Sequence[bytes],
    *,
    provider: str,
    model: str,
    api_key: SecretStr,
    timeout_s: float,
    transport: httpx2.AsyncBaseTransport | None = None,
) -> ExtractionOutcome:
    """Pide al proveedor que lea el documento. Lanza `ProviderError` si falla.

    La clave solo existe dentro de esta llamada: el adaptador crea su cliente,
    lo usa una vez y lo cierra.
    """
    adapter = get_adapter(provider)
    if adapter is None:
        raise ValueError(f"proveedor desconocido: {provider}")
    try:
        return await adapter.extract(
            pages, model=model, api_key=api_key, timeout_s=timeout_s, transport=transport
        )
    except ScanningError:
        raise
    except Exception as exc:
        # Cualquier excepción no prevista podría llevar la petición (y con ella
        # la clave) en sus atributos: solo se registra su tipo y se descarta.
        logger.warning(
            "fallo inesperado del adaptador",
            extra={"proveedor": provider, "tipo": type(exc).__name__},
        )
        raise ProveedorNoDisponible("El proveedor devolvió un error inesperado.") from None
