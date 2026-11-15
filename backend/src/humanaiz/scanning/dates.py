"""Interpretación de fechas leídas de un documento peruano (día primero)."""

from __future__ import annotations

import re
import unicodedata
from datetime import date

_MESES = {
    "ene": 1,
    "feb": 2,
    "mar": 3,
    "abr": 4,
    "may": 5,
    "jun": 6,
    "jul": 7,
    "ago": 8,
    "set": 9,
    "sep": 9,
    "oct": 10,
    "nov": 11,
    "dic": 12,
}

_ISO = re.compile(r"^(\d{4})[-/.](\d{1,2})[-/.](\d{1,2})$")
_DMY = re.compile(r"^(\d{1,2})[-/.\s](\d{1,2})[-/.\s](\d{2}|\d{4})$")
_TEXTO = re.compile(r"^(\d{1,2})\s*(?:de\s+)?([a-z]{3,10})\.?\s*(?:de\s+|del\s+)?(\d{2}|\d{4})$")


def _anio(valor: str) -> int:
    anio = int(valor)
    # Años de dos dígitos: un certificado vigente siempre es de este siglo.
    return anio + 2000 if anio < 100 else anio


def _construir(anio: int, mes: int, dia: int) -> date | None:
    try:
        fecha = date(anio, mes, dia)
    except ValueError:
        return None
    return fecha if 2000 <= fecha.year <= 2100 else None


def parse_fecha(texto: str | None) -> date | None:
    """Devuelve la fecha o None si el texto no es una fecha válida e inequívoca."""
    if not texto:
        return None
    limpio = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode()
    limpio = re.sub(r"\s+", " ", limpio).strip().lower()

    if m := _ISO.match(limpio):
        return _construir(int(m[1]), int(m[2]), int(m[3]))
    if m := _DMY.match(limpio):
        return _construir(_anio(m[3]), int(m[2]), int(m[1]))
    if m := _TEXTO.match(limpio):
        mes = _MESES.get(m[2][:3])
        return _construir(_anio(m[3]), mes, int(m[1])) if mes else None
    return None
