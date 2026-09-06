"""Agente Evaluador (Groq): match score y analisis de compatibilidad.

Hace UNA sola llamada a la IA por candidato para analizar su perfil frente a
los requisitos de la vacante. En `--dry-run` devuelve un ejemplo sin consumo.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from ..core.llm import PROVEEDOR_GROQ, ErrorModelo, generar_texto
from ..core.prompts import (
    ErrorPromptConfig,
    ErrorRespuestaIA,
    cargar_prompt,
    parsear_json,
)

LOG = logging.getLogger("agente_rrhh")


class ErrorAgenteEvaluador(Exception):
    """Fallo en la llamada al evaluador o en su respuesta."""


class AgenteEvaluador:
    def __init__(
        self,
        api_key: str,
        modelo: str,
        prompt_ruta: str,
    ) -> None:
        self._api_key = api_key
        self._modelo = modelo
        self._prompt_ruta = prompt_ruta

    def evaluar(
        self,
        perfil: dict[str, Any],
        requisitos: dict[str, Any],
        dry_run: bool = False,
    ) -> tuple[dict[str, Any], dict[str, int]]:
        """Devuelve (datos_ia, uso_tokens).  raised: ErrorAgenteEvaluador."""
        if dry_run:
            return self._simulado()

        try:
            prompt = cargar_prompt(
                self._prompt_ruta,
                {
                    "requisitos_vacante": json.dumps(
                        requisitos, ensure_ascii=False, indent=2
                    ),
                    "perfil_candidato": json.dumps(
                        perfil, ensure_ascii=False, indent=2
                    ),
                },
            )
            respuesta, uso = generar_texto(
                PROVEEDOR_GROQ, self._modelo, self._api_key, prompt,
            )
        except (ErrorPromptConfig, ErrorModelo) as exc:
            raise ErrorAgenteEvaluador(str(exc)) from exc

        LOG.debug("Tokens usados en evaluacion: %s", uso)
        try:
            datos = parsear_json(respuesta)
        except ErrorRespuestaIA as exc:
            raise ErrorAgenteEvaluador(str(exc)) from exc
        return datos, uso

    def _simulado(self) -> tuple[dict[str, Any], dict[str, int]]:
        """Modo --dry-run: devuelve un ejemplo sin llamar a la IA."""
        datos = {
            "desglose": {
                "habilidades": 100,
                "experiencia": 0,
                "formacion": 100,
            },
            "fortalezas": [],
            "brechas": [],
            "requisito_esencial_ausente": [],
            "justificacion": "Candidato simulado (dry-run).",
        }
        uso = {"prompt": 0, "completado": 0, "total": 0}
        return datos, uso