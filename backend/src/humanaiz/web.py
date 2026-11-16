"""La web compilada servida por la propia API (despliegue de un solo contenedor).

Con docker compose esto lo hace Caddy (deploy/Caddyfile). En plataformas que
ejecutan un único contenedor, como Vercel, la API sirve también el SPA desde
STATIC_DIR, con las mismas cabeceras: la CSP estricta es la principal defensa
de la clave de IA que el usuario guarda en el navegador, así que no puede faltar.
"""

from __future__ import annotations

import json
from pathlib import Path, PurePosixPath
from urllib.parse import unquote

from starlette.datastructures import MutableHeaders
from starlette.responses import FileResponse, Response
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from humanaiz.errors import error_body

CSP_WEB = (
    "default-src 'none'; script-src 'self'; style-src 'self' 'unsafe-inline'; "
    "img-src 'self' blob: data:; font-src 'self'; connect-src 'self'; manifest-src 'self'; "
    "base-uri 'none'; form-action 'self'; frame-ancestors 'none'"
)

# En todas las respuestas, web y API (como el bloque `header` del Caddyfile).
CABECERAS_COMUNES = {
    "Strict-Transport-Security": "max-age=31536000",
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "no-referrer",
    "Cross-Origin-Opener-Policy": "same-origin",
    "Permissions-Policy": "camera=(), microphone=(), geolocation=(), payment=()",
}

# Rutas internas que no se exponen hacia fuera (como `@interno` en el Caddyfile).
RUTAS_INTERNAS = ("/api/v1/health/ready", "/api/docs", "/api/openapi.json")

# Tipos explícitos: con `nosniff`, un JavaScript servido con otro tipo no se ejecuta.
_TIPOS = {
    ".html": "text/html; charset=utf-8",
    ".js": "text/javascript; charset=utf-8",
    ".mjs": "text/javascript; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".json": "application/json",
    ".webmanifest": "application/manifest+json",
    ".svg": "image/svg+xml",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".webp": "image/webp",
    ".ico": "image/x-icon",
    ".woff2": "font/woff2",
    ".txt": "text/plain; charset=utf-8",
}

# Los assets llevan hash en el nombre: inmutables, también en la CDN de la
# plataforma. El HTML se revalida siempre en el navegador; la CDN puede servir
# una copia breve mientras arranca un contenedor en frío (cada despliegue la invalida).
_CACHE_ASSETS = "public, max-age=31536000, immutable"
_CACHE_HTML = "no-cache"
_CDN_HTML = "max-age=60, stale-while-revalidate=86400"


class WebEstatica:
    """Middleware ASGI: /api/* va a la API; lo demás, a la web compilada."""

    def __init__(self, app: ASGIApp, directorio: Path) -> None:
        self.app = app
        self.raiz = directorio.resolve()
        self.indice = self.raiz / "index.html"
        if not self.indice.is_file():
            raise RuntimeError(f"STATIC_DIR no contiene index.html: {self.raiz}")

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        ruta: str = scope["path"]
        if ruta.startswith(RUTAS_INTERNAS):
            await self._respuesta(
                _error_json(404, "no_encontrado", "No encontrado."), scope, receive, send
            )
        elif ruta == "/api" or ruta.startswith("/api/"):
            await self.app(scope, receive, self._con_cabeceras(send))
        elif scope["method"] not in ("GET", "HEAD"):
            await self._respuesta(
                Response(status_code=405, headers={"Allow": "GET, HEAD"}), scope, receive, send
            )
        else:
            await self._respuesta(self._archivo(ruta), scope, receive, send)

    def _archivo(self, ruta: str) -> Response:
        relativa = PurePosixPath(unquote(ruta).lstrip("/"))
        if ".." in relativa.parts:
            return Response(status_code=404)
        candidato = (self.raiz / relativa).resolve() if relativa.parts else self.indice
        dentro = candidato == self.raiz or self.raiz in candidato.parents
        if dentro and candidato.is_file():
            es_asset = relativa.parts[:1] == ("assets",)
            cabeceras = {"Cache-Control": _CACHE_ASSETS if es_asset else _CACHE_HTML}
            if es_asset:
                cabeceras["Vercel-CDN-Cache-Control"] = _CACHE_ASSETS
            elif candidato == self.indice:
                cabeceras["Vercel-CDN-Cache-Control"] = _CDN_HTML
            return self._servir(candidato, cabeceras)
        # Un archivo con extensión que no existe es un 404 de verdad; cualquier
        # otra ruta es del SPA (react-router) y recibe index.html.
        if relativa.suffix:
            return Response(status_code=404, headers={"Cache-Control": "no-store"})
        return self._servir(
            self.indice, {"Cache-Control": _CACHE_HTML, "Vercel-CDN-Cache-Control": _CDN_HTML}
        )

    def _servir(self, archivo: Path, cabeceras: dict[str, str]) -> Response:
        tipo = _TIPOS.get(archivo.suffix.lower(), "application/octet-stream")
        return FileResponse(
            archivo,
            media_type=tipo,
            headers={**cabeceras, "Content-Security-Policy": CSP_WEB},
        )

    async def _respuesta(
        self, respuesta: Response, scope: Scope, receive: Receive, send: Send
    ) -> None:
        await respuesta(scope, receive, self._con_cabeceras(send))

    @staticmethod
    def _con_cabeceras(send: Send) -> Send:
        async def enviar(message: Message) -> None:
            if message["type"] == "http.response.start":
                headers = MutableHeaders(scope=message)
                for nombre, valor in CABECERAS_COMUNES.items():
                    headers.setdefault(nombre, valor)
                if "server" in headers:
                    del headers["server"]
            await send(message)

        return enviar


def _error_json(status: int, code: str, message: str) -> Response:
    return Response(
        json.dumps(error_body(code, message), ensure_ascii=False),
        status_code=status,
        media_type="application/json",
        headers={"Cache-Control": "no-store"},
    )
