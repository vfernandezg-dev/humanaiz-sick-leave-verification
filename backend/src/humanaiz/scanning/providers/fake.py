"""Proveedor simulado para pruebas: no hace red y es totalmente controlable.

No está en el catálogo ni en el registro por defecto: solo existe donde un
test lo registra de forma explícita.
"""

from __future__ import annotations

import asyncio
from collections.abc import Sequence
from dataclasses import dataclass, field

import httpx2
from pydantic import SecretStr

from humanaiz.scanning.types import Extraccion, ExtractionOutcome


@dataclass
class FakeAdapter:
    id: str = "fake"
    extraccion: Extraccion | None = None
    error: Exception | None = None
    # Si se define, la llamada espera a que el test lo active (simula latencia).
    continuar: asyncio.Event | None = None
    iniciada: asyncio.Event = field(default_factory=asyncio.Event)
    llamadas: list[dict[str, object]] = field(default_factory=list)

    async def extract(
        self,
        pages: Sequence[bytes],
        *,
        model: str,
        api_key: SecretStr,
        timeout_s: float,
        transport: httpx2.AsyncBaseTransport | None = None,
    ) -> ExtractionOutcome:
        # Se anota que llegó una clave, nunca su valor.
        self.llamadas.append(
            {"model": model, "paginas": len(pages), "con_clave": bool(api_key.get_secret_value())}
        )
        self.iniciada.set()
        if self.continuar is not None:
            await self.continuar.wait()
        if self.error is not None:
            raise self.error
        if self.extraccion is None:
            raise RuntimeError("FakeAdapter sin extracción configurada")
        return ExtractionOutcome(
            extraccion=self.extraccion,
            tokens_entrada=1200,
            tokens_salida=180,
            modelo_efectivo=model,
            request_id="req_fake_123",
        )
