"""Agente Extractor (Gemini): texto saneado a JSON estandarizado.

El prompt vive en un archivo Markdown (default `prompt/extractor.md`) para
poder configurarse sin tocar código. El placeholder `{{texto_candidato}}`
se sustituye con el texto del candidato en cada llamada.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from google.genai import Client

_FENCE_JSON = re.compile(r"^```(?:json)?\s*|\s*```$", re.MULTILINE)
_PLACEHOLDER = "{{texto_candidato}}"


def _cargar_prompt(ruta: str) -> str:
    archivo = Path(ruta)
    if not archivo.is_file():
        raise ErrorAgenteExtractor(
            f"No se encontro el archivo de prompt '{ruta}'. "
            f"Verifica PROMPT_EXTRACTOR en el archivo .env."
        )
    prompt = archivo.read_text(encoding="utf-8")
    if _PLACEHOLDER not in prompt:
        raise ErrorAgenteExtractor(
            f"El prompt '{ruta}' debe contener el placeholder {_PLACEHOLDER}."
        )
    return prompt


def _parsear_json(respuesta: str) -> dict[str, Any]:
    """Extrae y valida el JSON de la respuesta (tolera bloque ```json)."""
    respuesta = _FENCE_JSON.sub("", respuesta.strip())
    inicio = respuesta.find("{")
    fin = respuesta.rfind("}")
    if inicio == -1 or fin == -1 or fin <= inicio:
        raise ValueError("La respuesta de Gemini no contiene un objeto JSON valido.")

    datos = json.loads(respuesta[inicio : fin + 1])
    if not isinstance(datos, dict):
        raise ValueError("La respuesta de Gemini no es un objeto JSON.")
    return datos


class ErrorAgenteExtractor(Exception):
    """Fallo de la llamada a la API de Gemini o de su respuesta."""


class AgenteExtractor:
    def __init__(
        self,
        api_key: str,
        modelo: str = "gemini-3.5-flash",
        prompt_ruta: str = "prompt/extractor.md",
    ) -> None:
        self._modelo = modelo
        self._prompt_ruta = prompt_ruta
        self._cliente: Client | None = Client(api_key=api_key) if api_key else None

    def extraer(self, texto: str, dry_run: bool = False) -> dict[str, Any]:
        if dry_run:
            return self._extraer_simulado(texto)
        if self._cliente is None:
            raise ErrorAgenteExtractor(
                "GEMINI_API_KEY no esta configurada en el archivo .env. "
                "Sin la clave real solo puede usar el modo --dry-run."
            )

        try:
            prompt = _cargar_prompt(self._prompt_ruta)
            contenido = prompt.replace(_PLACEHOLDER, texto)
            respuesta = self._cliente.models.generate_content(
                model=self._modelo, contents=contenido
            )
        except ErrorAgenteExtractor:
            raise
        except Exception as exc:
            raise ErrorAgenteExtractor(f"Fallo la llamada a Gemini: {exc}") from exc

        texto_respuesta = respuesta.text or ""
        if not texto_respuesta.strip():
            raise ErrorAgenteExtractor("Gemini devolvio una respuesta vacia.")
        return _parsear_json(texto_respuesta)

    def _extraer_simulado(self, _texto: str) -> dict[str, Any]:
        """Modo --dry-run: devuelve un JSON de ejemplo sin consumir la API."""
        return {
            "candidato": {"email_remitente": "", "formato_origen": "DRY-RUN"},
            "datos_estructurados": {
                "habilidades": [],
                "experiencia_laboral": [],
                "formacion_academica": [],
                "certificaciones": [],
            },
            "control_sesgo": {
                "atributos_excluidos": ["foto", "edad", "genero", "direccion", "estado_civil"]
            },
            "modo": "dry_run",
        }