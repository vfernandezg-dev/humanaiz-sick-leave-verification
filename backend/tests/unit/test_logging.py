from __future__ import annotations

import json
import logging

from humanaiz.logging import REDACTED, JsonFormatter, redact, request_id_var


def test_redacta_claves_de_proveedores() -> None:
    texto = (
        "fallo con sk-ant-api03-AbCdEfGh12345678 y AIzaSyA1234567890abcdefghijklmn "
        "y sk-proj-abcdefghijklmnop1234"
    )
    limpio = redact(texto)
    assert "sk-ant" not in limpio
    assert "AIza" not in limpio
    assert "sk-proj" not in limpio
    assert limpio.count(REDACTED) == 3


def test_formato_json_incluye_request_id_y_extras() -> None:
    record = logging.LogRecord("prueba", logging.INFO, __file__, 1, "hola %s", ("mundo",), None)
    record.status = 200
    token = request_id_var.set("abc123")
    try:
        payload = json.loads(JsonFormatter().format(record))
    finally:
        request_id_var.reset(token)
    assert payload["msg"] == "hola mundo"
    assert payload["request_id"] == "abc123"
    assert payload["status"] == 200
    assert payload["level"] == "INFO"


def test_traceback_no_filtra_secretos() -> None:
    try:
        raise RuntimeError("clave sk-ant-api03-SECRETO1234567890")
    except RuntimeError:
        import sys

        record = logging.LogRecord("prueba", logging.ERROR, __file__, 1, "boom", (), sys.exc_info())
    salida = JsonFormatter().format(record)
    assert "SECRETO" not in salida
    assert REDACTED in salida
