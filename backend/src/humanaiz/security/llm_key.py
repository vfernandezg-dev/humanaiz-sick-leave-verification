"""Lectura de la clave de IA que el usuario envía en cada petición (BYOK).

La clave se lee a mano de la cabecera, no con `Header()` de FastAPI: un
parámetro declarado y validado por el framework se devolvería en el cuerpo de
un error 422. Se envuelve en `SecretStr` para que no aparezca en `repr`, logs
ni volcados de modelos, y nunca se guarda: ni en base de datos, ni en caché, ni
como huella o "últimos 4 caracteres".
"""

from __future__ import annotations

from fastapi import Request
from pydantic import SecretStr

from humanaiz.errors import AppError

LLM_KEY_HEADER = "x-llm-api-key"
_MIN_LEN = 16
_MAX_LEN = 512


def read_llm_key(request: Request) -> SecretStr:
    raw = request.headers.get(LLM_KEY_HEADER)
    if raw is None or not raw.strip():
        raise AppError(
            400, "llm_clave_faltante", "Configura tu clave de IA para poder analizar documentos."
        )
    key = raw.strip()
    if (
        not _MIN_LEN <= len(key) <= _MAX_LEN
        or not key.isascii()
        or not key.isprintable()
        or " " in key
    ):
        # El mensaje no repite nada de lo recibido.
        raise AppError(
            400, "llm_clave_faltante", "La clave de IA no tiene un formato válido. Revísala."
        )
    return SecretStr(key)
