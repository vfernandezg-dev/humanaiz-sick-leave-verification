"""Middleware ASGI puro: id de petición, límite de cuerpo, cabeceras y log de acceso.

Se evita `BaseHTTPMiddleware` a propósito: cancela el endpoint cuando el
cliente se desconecta, y un análisis ya pagado por el usuario debe terminar.
"""

from __future__ import annotations

import json
import logging
import time
import uuid
from collections.abc import Callable

from fastapi import HTTPException
from starlette.datastructures import MutableHeaders
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from humanaiz.errors import AppError, error_body
from humanaiz.logging import request_id_var

logger = logging.getLogger("humanaiz.access")

BodyLimit = Callable[[str, str], int]


def demasiado_grande() -> AppError:
    return AppError(
        413, "archivo_demasiado_grande", "El contenido enviado supera el tamaño permitido."
    )


class RequestContextMiddleware:
    def __init__(self, app: ASGIApp, *, body_limit: BodyLimit) -> None:
        self.app = app
        self.body_limit = body_limit

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request_id = uuid.uuid4().hex
        token = request_id_var.set(request_id)
        started = time.perf_counter()
        status_code = 500
        method: str = scope["method"]
        path: str = scope["path"]
        limit = self.body_limit(method, path)
        received = 0

        async def limited_receive() -> Message:
            nonlocal received
            message = await receive()
            if message["type"] == "http.request":
                received += len(message.get("body", b""))
                if received > limit:
                    # HTTPException y no AppError: FastAPI convierte en 400
                    # cualquier otra excepción lanzada mientras lee el cuerpo.
                    raise HTTPException(status_code=413)
            return message

        async def send_with_headers(message: Message) -> None:
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = message["status"]
                headers = MutableHeaders(scope=message)
                headers["X-Request-ID"] = request_id
                headers.setdefault("Cache-Control", "no-store")
                headers.setdefault("X-Content-Type-Options", "nosniff")
            await send(message)

        try:
            declared = _content_length(scope)
            if declared is not None and declared > limit:
                await _send_error(send_with_headers, demasiado_grande())
                return
            await self.app(scope, limited_receive, send_with_headers)
        finally:
            # Solo método, ruta y estado: nunca cabeceras ni query string.
            logger.info(
                "%s %s %s",
                method,
                path,
                status_code,
                extra={
                    "method": method,
                    "path": path,
                    "status": status_code,
                    "duration_ms": round((time.perf_counter() - started) * 1000, 1),
                },
            )
            request_id_var.reset(token)


def _content_length(scope: Scope) -> int | None:
    for name, value in scope.get("headers", ()):
        if name == b"content-length":
            try:
                return int(value)
            except ValueError:
                return None
    return None


async def _send_error(send: Send, exc: AppError) -> None:
    body = json.dumps(error_body(exc.code, exc.message), ensure_ascii=False).encode()
    await send(
        {
            "type": "http.response.start",
            "status": exc.status_code,
            "headers": [
                (b"content-type", b"application/json"),
                (b"content-length", str(len(body)).encode()),
            ],
        }
    )
    await send({"type": "http.response.body", "body": body})
