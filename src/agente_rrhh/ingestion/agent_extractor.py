"""Agente Extractor (Gemini): texto saneado a JSON estandarizado.

El prompt vive en un archivo Markdown (default `prompt/extractor.md`) para
poder configurarse sin tocar código. El placeholder `{{texto_candidato}}`
se sustituye con el texto del candidato en cada llamada. Toda la llamada a la
IA pasa por `core.llm` (un solo proveedor de IA configurado).
"""

from __future__ import annotations

import logging
from typing import Any

from ..core.llm import PROVEEDOR_GEMINI, ErrorModelo, generar_texto
from ..core.prompts import (
    ErrorPromptConfig,
    ErrorRespuestaIA,
    cargar_prompt,
    parsear_json,
)

LOG = logging.getLogger("agente_rrhh")

_PLACEHOLDER = "texto_candidato"


class ErrorAgenteExtractor(Exception):
    """Fallo de la llamada a la API de Gemini o de su respuesta."""


class AgenteExtractor:
    def __init__(
        self,
        api_key: str,
        modelo: str = "gemini-3.5-flash",
        prompt_ruta: str = "prompt/extractor.md",
    ) -> None:
        self._api_key = api_key
        self._modelo = modelo
        self._prompt_ruta = prompt_ruta

    def extraer(self, texto: str, dry_run: bool = False) -> dict[str, Any]:
        if dry_run:
            return self._extraer_simulado(texto)

        try:
            prompt = cargar_prompt(self._prompt_ruta, {_PLACEHOLDER: texto})
            respuesta, uso = generar_texto(
                PROVEEDOR_GEMINI, self._modelo, self._api_key, prompt
            )
        except ErrorPromptConfig as exc:
            raise ErrorAgenteExtractor(str(exc)) from exc
        except ErrorModelo as exc:
            raise ErrorAgenteExtractor(str(exc)) from exc

        LOG.debug("Tokens usados en extraccion: %s", uso)
        try:
            return parsear_json(respuesta)
        except ErrorRespuestaIA as exc:
            raise ErrorAgenteExtractor(str(exc)) from exc

    def _extraer_simulado(self, _texto: str) -> dict[str, Any]:
        """Modo --dry-run: devuelve un JSON de ejemplo sin consumir la API."""
        return {
            "candidato": {"email_remitente": "", "formato_origen": "DRY-RUN"},
            "datos_contacto": {
                "nombre_completo": "",
                "telefono": "",
                "email": "",
            },
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