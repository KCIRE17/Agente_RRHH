"""Sanitización del texto extraído: normalización UTF-8, tildes y espacios."""

from __future__ import annotations

import re
import unicodedata

_CONTROL = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
_MULTIESPACIO = re.compile(r"[ \t]+")
_LINEAS_VACIAS = re.compile(r"\n{3,}")


def quitar_tildes(texto: str) -> str:
    """Normaliza la codificación y elimina tildes (e.g. 'Sistemas' -> 'Sistemas')."""
    normalizado = unicodedata.normalize("NFKD", texto)
    return "".join(c for c in normalizado if not unicodedata.combining(c))


def sanitizar(texto: str) -> str:
    """Normaliza el texto crudo de un documento para el Agente Extractor."""
    if not texto:
        return ""

    texto = _CONTROL.sub("", texto)
    texto = texto.replace("\r\n", "\n").replace("\r", "\n")
    texto = unicodedata.normalize("NFKC", texto)
    texto = _MULTIESPACIO.sub(" ", texto)
    texto = _LINEAS_VACIAS.sub("\n\n", texto)
    texto = quitar_tildes(texto)
    return texto.strip()