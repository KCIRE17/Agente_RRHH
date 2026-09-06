"""Persistencia de evaluaciones (capa gold del medallion).

- ``data/gold/evaluacion/<vacante>/<id_candidato>.json``: documento evaluado.
- ``data/gold/evaluacion/<vacante>/ranking.json``: lista ordenada por score.
"""

from __future__ import annotations

import json
import logging
import os
import tempfile
from pathlib import Path
from typing import Any

from .vacantes import slug_vacante

LOG = logging.getLogger("agente_rrhh")


class GoldStore:
    """Guarda y lee documentos de evaluacion por vacante en gold."""

    def __init__(self, dir_base: str | Path, subcarpeta: str = "evaluacion") -> None:
        self._dir = Path(dir_base) / subcarpeta
        self._dir.mkdir(parents=True, exist_ok=True)

    def _carpeta_vacante(self, vacante_id: str) -> Path:
        carpeta = self._dir / slug_vacante(vacante_id)
        carpeta.mkdir(parents=True, exist_ok=True)
        return carpeta

    def ruta_candidato(self, vacante_id: str, id_candidato: str) -> Path:
        return self._carpeta_vacante(vacante_id) / f"{id_candidato}.json"

    def _ruta_ranking(self, vacante_id: str) -> Path:
        return self._carpeta_vacante(vacante_id) / "ranking.json"

    def existe_evaluacion(self, vacante_id: str, id_candidato: str) -> bool:
        return self.ruta_candidato(vacante_id, id_candidato).exists()

    def guardar_evaluacion(self, vacante_id: str, documento: dict[str, Any]) -> None:
        ruta = self.ruta_candidato(
            vacante_id, documento.get("id_candidato", "sincandidato")
        )
        self._escribir(ruta, documento)
        self._recalcular_ranking(vacante_id)

    def _recalcular_ranking(self, vacante_id: str) -> None:
        carpeta = self._carpeta_vacante(vacante_id)
        filas = []
        for ruta in sorted(carpeta.glob("*.json")):
            if ruta.name == "ranking.json":
                continue
            doc = self._leer(ruta)
            if doc and isinstance(doc.get("match_score"), (int, float)):
                filas.append(
                    {
                        "vacante_id": doc.get("vacante_id"),
                        "id_candidato": doc.get("id_candidato"),
                        "nombre": doc.get("nombre_completo"),
                        "email_remitente": doc.get("email_remitente"),
                        "match_score": round(float(doc["match_score"]), 2),
                        "clasificacion": doc.get("clasificacion"),
                        "fecha_evaluacion": doc.get("fecha_evaluacion"),
                    }
                )
        filas.sort(key=lambda f: f["match_score"], reverse=True)
        self._escribir(
            self._ruta_ranking(vacante_id),
            {"vacante_id": vacante_id, "total": len(filas), "candidatos": filas},
        )

    # ------------------------------------------------------------ bajo nivel
    def _leer(self, ruta: Path) -> dict[str, Any] | None:
        try:
            with ruta.open("r", encoding="utf-8") as f:
                return json.load(f)
        except (OSError, json.JSONDecodeError) as exc:
            LOG.warning("No se pudo leer %s: %s", ruta, exc)
            return None

    def _escribir(self, ruta: Path, documento: dict[str, Any]) -> None:
        ruta.parent.mkdir(parents=True, exist_ok=True)
        fd, temporal = tempfile.mkstemp(
            dir=str(ruta.parent), suffix=".tmp", prefix=".escribiendo-"
        )
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(documento, f, ensure_ascii=False, indent=2)
            os.replace(temporal, ruta)
        finally:
            if os.path.exists(temporal):
                os.unlink(temporal)