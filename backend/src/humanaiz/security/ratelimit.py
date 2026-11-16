"""Límites de uso con la librería `limits` (ventana móvil).

Con `memory://` los contadores viven en el proceso: exacto con una sola
réplica. Para varias réplicas se configura `redis://…` en RATE_LIMIT_STORAGE_URI.
Las claves nunca derivan de la clave de IA del usuario.
"""

from __future__ import annotations

import ipaddress
import math
import time

from fastapi import Request
from limits import RateLimitItem, parse
from limits.aio.strategies import MovingWindowRateLimiter
from limits.storage import storage_from_string

from humanaiz.errors import AppError

# El tope por IP es más holgado que el por cuenta: muchas personas pueden
# compartir una IP (redes móviles con CGNAT, oficinas).
FACTOR_LIMITE_IP = 3


class RateLimiter:
    def __init__(self, storage_uri: str) -> None:
        uri = storage_uri if storage_uri.startswith("async+") else f"async+{storage_uri}"
        self._strategy = MovingWindowRateLimiter(storage_from_string(uri))
        self._parsed: dict[str, RateLimitItem] = {}

    def _item(self, limit: str) -> RateLimitItem:
        if limit not in self._parsed:
            self._parsed[limit] = parse(limit)
        return self._parsed[limit]

    async def check(
        self,
        limit: str,
        *key: str,
        code: str = "rate_limit",
        message: str = "Demasiadas solicitudes. Espera un momento antes de volver a intentarlo.",
    ) -> None:
        """Cuenta un uso y lanza 429 con Retry-After si se superó el límite."""
        item = self._item(limit)
        if await self._strategy.hit(item, *key):
            return
        stats = await self._strategy.get_window_stats(item, *key)
        retry_after = max(1, math.ceil(stats.reset_time - time.time()))
        raise AppError(429, code, message, headers={"Retry-After": str(retry_after)})

    async def check_en_capas(
        self,
        accion: str,
        *,
        limite: str,
        usuario: str,
        ip: str,
        limite_global: str | None = None,
    ) -> None:
        """Aplica un límite por usuario, otro por IP y, opcionalmente, uno total.

        Los dos primeros se esquivan cambiando de navegador, de IP o usando una
        VPN: sirven para repartir el uso con justicia. El total no depende de
        quién llama y es el que acota de verdad la carga del servidor; si se
        agota, el servicio responde "vuelve más tarde" a todos por igual.
        """
        await self.check(limite, accion, usuario)
        await self.check(scale_limit(limite, FACTOR_LIMITE_IP), f"{accion}-ip", ip)
        if limite_global:
            await self.check(
                limite_global,
                f"{accion}-global",
                code="capacidad_agotada",
                message=(
                    "El servicio alcanzó su capacidad por ahora. "
                    "Vuelve a intentarlo en unos minutos."
                ),
            )


def scale_limit(limit: str, factor: int) -> str:
    """'5/minute' x4 -> '20/minute'. Para el tope por IP, más holgado que el por cuenta."""
    amount, _, rest = limit.partition("/")
    return f"{int(amount.strip()) * factor}/{rest.strip()}"


def client_ip(request: Request) -> str:
    """IP del cliente tal como la fija uvicorn desde el proxy de confianza.

    IPv6 se agrupa por /64: un solo host controla 2^64 direcciones de su prefijo.
    """
    host = request.client.host if request.client else ""
    try:
        ip = ipaddress.ip_address(host)
    except ValueError:
        return "desconocida"
    if isinstance(ip, ipaddress.IPv6Address):
        if ip.ipv4_mapped is not None:
            return str(ip.ipv4_mapped)
        return str(ipaddress.ip_network(f"{ip}/64", strict=False).network_address)
    return str(ip)


def get_limiter(request: Request) -> RateLimiter:
    return request.app.state.limiter


async def general_rate_limit(request: Request) -> None:
    """Tope amplio por IP para toda la API."""
    limiter: RateLimiter = request.app.state.limiter
    await limiter.check(
        request.app.state.settings.rate_limit_general, "general", client_ip(request)
    )
