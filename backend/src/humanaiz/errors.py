"""Errores de aplicación y su representación única en la API."""

from __future__ import annotations

import logging
from collections.abc import Mapping, Sequence
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from humanaiz.logging import request_id_var

logger = logging.getLogger(__name__)


class AppError(Exception):
    """Error esperado, con código estable y mensaje apto para mostrar al usuario."""

    def __init__(
        self,
        status_code: int,
        code: str,
        message: str,
        *,
        detalles: Sequence[Mapping[str, str]] | None = None,
        headers: Mapping[str, str] | None = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.message = message
        self.detalles = list(detalles) if detalles else None
        self.headers = dict(headers) if headers else None


def no_encontrado(message: str = "No se encontró el recurso solicitado.") -> AppError:
    return AppError(404, "no_encontrado", message)


def prohibido(message: str = "No tienes permiso para realizar esta acción.") -> AppError:
    return AppError(403, "prohibido", message)


def no_autenticado(code: str = "no_autenticado", message: str = "Inicia sesión.") -> AppError:
    return AppError(401, code, message, headers={"WWW-Authenticate": "Bearer"})


def conflicto(code: str, message: str) -> AppError:
    return AppError(409, code, message)


def invalido(code: str, message: str, campo: str | None = None) -> AppError:
    detalles = [{"campo": campo, "mensaje": message}] if campo else None
    return AppError(422, code, message, detalles=detalles)


def error_body(
    code: str, message: str, detalles: Sequence[Mapping[str, Any]] | None = None
) -> dict[str, Any]:
    body: dict[str, Any] = {"code": code, "message": message}
    if detalles:
        body["detalles"] = list(detalles)
    request_id = request_id_var.get()
    if request_id:
        body["request_id"] = request_id
    return {"error": body}


_HTTP_CODES = {
    400: ("solicitud_invalida", "La solicitud no es válida."),
    401: ("no_autenticado", "Inicia sesión."),
    403: ("prohibido", "No tienes permiso para realizar esta acción."),
    404: ("no_encontrado", "No se encontró el recurso solicitado."),
    405: ("metodo_no_permitido", "Método no permitido."),
    413: ("archivo_demasiado_grande", "El contenido enviado supera el tamaño permitido."),
    415: ("tipo_no_soportado", "Tipo de contenido no soportado."),
}


def install_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def _app_error(_: Request, exc: AppError) -> JSONResponse:
        return JSONResponse(
            error_body(exc.code, exc.message, exc.detalles),
            status_code=exc.status_code,
            headers=exc.headers,
        )

    @app.exception_handler(RequestValidationError)
    async def _validation_error(_: Request, exc: RequestValidationError) -> JSONResponse:
        # Nunca se devuelve `input` ni `ctx`: podrían reflejar datos sensibles.
        detalles = [
            {
                "campo": ".".join(str(p) for p in err.get("loc", ()) if p not in ("body", "query")),
                "mensaje": str(err.get("msg", "Valor no válido")),
            }
            for err in exc.errors()
        ]
        return JSONResponse(
            error_body("validacion", "Revisa los datos enviados.", detalles), status_code=422
        )

    @app.exception_handler(StarletteHTTPException)
    async def _http_error(_: Request, exc: StarletteHTTPException) -> JSONResponse:
        code, message = _HTTP_CODES.get(exc.status_code, ("error", "No se pudo completar."))
        return JSONResponse(
            error_body(code, message),
            status_code=exc.status_code,
            headers=getattr(exc, "headers", None),
        )

    @app.exception_handler(Exception)
    async def _unhandled(request: Request, exc: Exception) -> JSONResponse:
        logger.error(
            "error no controlado en %s %s",
            request.method,
            request.url.path,
            exc_info=(type(exc), exc, exc.__traceback__),
        )
        return JSONResponse(
            error_body("error_interno", "Ocurrió un error inesperado. Inténtalo de nuevo."),
            status_code=500,
        )
