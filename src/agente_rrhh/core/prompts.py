"""Carga de prompts editables y parseo de respuestas JSON de la IA.

Compartido por los agentes de F1 (extracción) y F2 (evaluación) para no
duplicar lógica entre fases.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

_FENCE_JSON = re.compile(r"^```(?:json)?\s*|\s*```$", re.MULTILINE)


class ErrorPromptConfig(Exception):
    """El archivo de prompt falta o no tiene los placeholders esperados."""


class ErrorRespuestaIA(Exception):
    """La respuesta de la IA no es un JSON válido."""


def cargar_prompt(ruta: str, placeholders: dict[str, str] | None = None) -> str:
    """Carga un prompt Markdown y sustituye los placeholders ``{{clave}}``."""
    archivo = Path(ruta)
    if not archivo.is_file():
        raise ErrorPromptConfig(
            f"No se encontro el archivo de prompt '{ruta}'. "
            "Verifica la variable correspondiente en el archivo .env."
        )
    prompt = archivo.read_text(encoding="utf-8")
    for clave, valor in (placeholders or {}).items():
        token = "{{" + clave + "}}"
        if token not in prompt:
            raise ErrorPromptConfig(
                f"El prompt '{ruta}' debe contener el placeholder {token}."
            )
        prompt = prompt.replace(token, valor)
    return prompt


def parsear_json(respuesta: str) -> dict[str, Any]:
    """Extrae y valida el JSON de la respuesta (tolera bloque ```json)."""
    respuesta = _FENCE_JSON.sub("", respuesta.strip())
    inicio = respuesta.find("{")
    fin = respuesta.rfind("}")
    if inicio == -1 or fin == -1 or fin <= inicio:
        raise ErrorRespuestaIA(
            "La respuesta de la IA no contiene un objeto JSON valido."
        )
    try:
        datos = json.loads(respuesta[inicio : fin + 1])
    except json.JSONDecodeError as exc:
        raise ErrorRespuestaIA(
            f"La respuesta de la IA no es un JSON valido: {exc}"
        ) from exc
    if not isinstance(datos, dict):
        raise ErrorRespuestaIA("La respuesta de la IA no es un objeto JSON.")
    return datos