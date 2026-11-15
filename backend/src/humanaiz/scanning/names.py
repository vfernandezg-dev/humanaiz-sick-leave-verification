"""Comparación de nombres de persona tolerante a tildes, orden y erratas de lectura."""

from __future__ import annotations

import re
import unicodedata

from rapidfuzz.distance import Levenshtein

_PARTICULAS = frozenset({"DE", "DEL", "LA", "LAS", "LOS", "Y", "E", "VDA", "VIUDA"})
_NO_LETRAS = re.compile(r"[^A-Z]+")


def tokens(nombre: str) -> list[str]:
    """'Pérez-Gómez, Ana María de la Cruz' -> ['PEREZ', 'GOMEZ', 'ANA', 'MARIA', 'CRUZ']."""
    sin_tildes = unicodedata.normalize("NFKD", nombre).encode("ascii", "ignore").decode()
    palabras = _NO_LETRAS.sub(" ", sin_tildes.upper()).split()
    return [p for p in palabras if p not in _PARTICULAS]


def _erratas_toleradas(palabra: str) -> int:
    """Letras de diferencia que se aceptan como error de lectura.

    Ninguna en palabras cortas: en "LUZ"/"LUIS" o "SOTO"/"SOSA" un carácter
    cambia a la persona. Una en palabras medianas ("RAMIRES"/"RAMIREZ",
    "GONZALES"/"GONZALEZ") y dos en las largas.
    """
    if len(palabra) <= 4:
        return 0
    return 1 if len(palabra) <= 8 else 2


def _aparece(palabra: str, en_documento: list[str]) -> bool:
    tolerancia = _erratas_toleradas(palabra)
    if tolerancia == 0:
        return palabra in en_documento
    return any(
        Levenshtein.distance(palabra, otra, score_cutoff=tolerancia) <= tolerancia
        for otra in en_documento
    )


def nombre_coincide(nombre_documento: str, nombres: str, apellidos: str) -> bool:
    """True si el documento nombra a la persona del sistema.

    Exige todos los apellidos y al menos un nombre de pila. Una comparación
    "difusa" del texto completo daría por buena una sola palabra común: un
    documento que solo dijera "JUAN" coincidiría con cualquier Juan.
    """
    en_documento = tokens(nombre_documento)
    apellidos_tokens = tokens(apellidos)
    nombres_tokens = tokens(nombres)
    if not en_documento or not apellidos_tokens or not nombres_tokens:
        return False
    todos_los_apellidos = all(_aparece(a, en_documento) for a in apellidos_tokens)
    algun_nombre = any(_aparece(n, en_documento) for n in nombres_tokens)
    return todos_los_apellidos and algun_nombre
