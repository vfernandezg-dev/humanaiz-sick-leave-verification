"""Normalización de imágenes: lanza el proceso hijo y recoge el resultado."""

from __future__ import annotations

import asyncio
import json
import os
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

from humanaiz.scanning.errors import DocumentoInvalido
from humanaiz.scanning.sniff import DocumentKind

_WORKER = "humanaiz.scanning._normalize_worker"


@dataclass(frozen=True, slots=True)
class Limits:
    max_pixels: int = 25_000_000
    min_side_px: int = 400
    page_max_side_px: int = 2400
    timeout_seconds: int = 15


@dataclass(frozen=True, slots=True)
class NormalizedDocument:
    kind: DocumentKind
    # Una imagen JPEG generada por nosotros: sin metadatos y con tamaño acotado.
    # Es lo único que se guarda, se muestra en pantalla o se envía a un modelo.
    pages: tuple[bytes, ...]


def _worker_env() -> dict[str, str]:
    # Entorno mínimo: el proceso que parsea archivos no confiables no hereda
    # secretos de la API (JWT_SECRET, DATABASE_URL...).
    env = {"PYTHONDONTWRITEBYTECODE": "1"}
    for name in ("SYSTEMROOT", "PATH", "TEMP", "TMP"):
        if name in os.environ:
            env[name] = os.environ[name]
    return env


def _run_worker(data: bytes, kind: DocumentKind, limits: Limits) -> tuple[bytes, ...]:
    workdir = Path(tempfile.mkdtemp(prefix="hz-norm-"))
    try:
        entrada = workdir / "entrada.bin"
        salida = workdir / "salida"
        salida.mkdir()
        entrada.write_bytes(data)
        args = [
            sys.executable,
            "-I",
            "-m",
            _WORKER,
            kind.value,
            str(entrada),
            str(salida),
            str(limits.max_pixels),
            str(limits.min_side_px),
            str(limits.page_max_side_px),
            str(limits.timeout_seconds),
        ]
        try:
            # `run` mata al hijo si vence el plazo: es la única forma fiable de
            # cortar una imagen que cuelga al decodificador.
            completed = subprocess.run(  # noqa: S603
                args,
                env=_worker_env(),
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=limits.timeout_seconds,
                check=False,
            )
        except subprocess.TimeoutExpired:
            raise DocumentoInvalido(
                "La imagen tardó demasiado en procesarse. Prueba con una versión más simple."
            ) from None

        resultado_path = salida / "result.json"
        if completed.returncode != 0 or not resultado_path.exists():
            # El decodificador murió (límite de memoria/CPU o fallo nativo).
            raise DocumentoInvalido("No se pudo procesar la imagen. Puede estar dañada.")
        resultado = json.loads(resultado_path.read_text(encoding="utf-8"))
        if not resultado.get("ok"):
            raise DocumentoInvalido(
                str(resultado.get("message", "Archivo no válido.")),
                code=str(resultado.get("code", "archivo_invalido")),
            )
        paginas = int(resultado["paginas"])
        return tuple((salida / f"page-{n}.jpg").read_bytes() for n in range(1, paginas + 1))
    finally:
        shutil.rmtree(workdir, ignore_errors=True)


async def normalize(data: bytes, kind: DocumentKind, limits: Limits) -> NormalizedDocument:
    """Valida y re-codifica la imagen. Lanza `DocumentoInvalido` si no es aceptable."""
    pages = await asyncio.to_thread(_run_worker, data, kind, limits)
    return NormalizedDocument(kind=kind, pages=pages)
