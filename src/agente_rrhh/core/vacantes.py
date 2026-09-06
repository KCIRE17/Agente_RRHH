"""Requisitos por vacante (regla de negocio) desde config/vacantes/*.json."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

_QUITAR_ACENTOS = str.maketrans(
    "ÁÉÍÓÚÜÑáéíóúüñ", "AEIOUUNaeiouun"
)


def slug_vacante(vacante_id: str) -> str:
    """Normaliza un id de vacante para nombres de archivo y carpetas."""
    limpio = vacante_id.strip().upper().translate(_QUITAR_ACENTOS)
    limpio = re.sub(r"[^A-Z0-9_\- ]+", "", limpio)
    return re.sub(r"\s+", "_", limpio) or "SIN_VACANTE"


class ErrorRequisitos(Exception):
    """No existen requisitos cargados para la vacante o son invalidos."""


class RequisitosVacante:
    """Carga el JSON editable de requisitos correspondiente a una vacante."""

    def __init__(self, dir_base: str | Path) -> None:
        self._dir = Path(dir_base)
        self._dir.mkdir(parents=True, exist_ok=True)

    def cargar(self, vacante_id: str) -> dict[str, Any]:
        archivo = self._dir / f"{slug_vacante(vacante_id)}.json"
        if not archivo.is_file():
            raise ErrorRequisitos(
                f"No existen requisitos para la vacante '{vacante_id}'. "
                f"Crea el archivo {archivo} (regla de negocio editable)."
            )
        try:
            with archivo.open("r", encoding="utf-8") as f:
                datos = json.load(f)
        except (OSError, json.JSONDecodeError) as exc:
            raise ErrorRequisitos(
                f"No se pudo leer los requisitos '{archivo}': {exc}"
            ) from exc
        if "requisitos" not in datos:
            raise ErrorRequisitos(
                f"El archivo '{archivo}' no tiene el campo 'requisitos'."
            )
        return datos