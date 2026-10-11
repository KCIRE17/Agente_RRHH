"""Diccionario de habilidades por nivel de negocio (config/habilidades.json).

F2 lo usa para decirle a la IA qué nivel de cada herramienta representa valor
real para la empresa. La coincidencia de habilidades sigue delegada a la IA;
este diccionario solo enriquece el contexto con los niveles/pesos definidos.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

LOG = logging.getLogger("agente_rrhh")

_PESOS_DEFECTO = {"basico": 1, "intermedio": 2, "avanzado": 3, "experto": 4}


def cargar_diccionario(ruta: str | Path) -> dict[str, Any]:
    """Carga el diccionario; devuelve {} si el archivo no existe o es inválido."""
    try:
        with Path(ruta).open("r", encoding="utf-8") as f:
            datos = json.load(f)
    except (OSError, json.JSONDecodeError) as exc:
        LOG.warning("No se pudo cargar el diccionario de habilidades %s: %s", ruta, exc)
        return {}
    if not isinstance(datos, dict):
        return {}
    return datos


def nivel_de(diccionario: dict[str, Any], habilidad: str) -> dict[str, Any] | None:
    """Devuelve la entrada del diccionario para una habilidad (sin tildes/espacios)."""
    habilidades = diccionario.get("habilidades") or {}
    clave = (habilidad or "").strip().lower()
    if clave in habilidades:
        return habilidades[clave]
    clave_sin_tildes = _sin_tildes(clave)
    for nombre, entrada in habilidades.items():
        if _sin_tildes(nombre) == clave_sin_tildes:
            return entrada
    return None


def _sin_tildes(texto: str) -> str:
    reemplazos = str.maketrans(
        "áéíóúüñàèìòùâêîôû", "aeiouunaeiouaeiou"
    )
    return texto.translate(reemplazos)


def resumen_para_prompt(diccionario: dict[str, Any]) -> dict[str, str]:
    """Diccionario plano {habilidad: nivel} para inyectar como contexto a la IA."""
    habilidades = diccionario.get("habilidades") or {}
    return {
        nombre: str(entrada.get("nivel", ""))
        for nombre, entrada in habilidades.items()
        if isinstance(entrada, dict)
    }


def pesos_por_nivel(diccionario: dict[str, Any]) -> dict[str, int]:
    """Pesos numéricos por nivel (con defaults si el archivo no los trae)."""
    pesos = diccionario.get("pesos_por_nivel") or _PESOS_DEFECTO
    return {str(k): int(v) for k, v in pesos.items()}
