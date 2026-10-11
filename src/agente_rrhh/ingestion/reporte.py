"""Reportes de la capa silver (F1) sin depender del dashboard.

- ``resumen_por_vacante``: total y desglose de estados por ``vacante_id``.
- ``ultima_fecha_procesada`` / ``dias_desde_ultima``: soporte del lote
  "desde la última ejecución" (en lugar de depender de ``DIAS_ATRAS``).
"""

from __future__ import annotations

import json
import logging
from collections import Counter
from datetime import date, datetime
from pathlib import Path
from typing import Any

LOG = logging.getLogger("agente_rrhh")


def _leer_documentos(silver_dir: str | Path) -> list[dict[str, Any]]:
    base = Path(silver_dir) / "candidatos"
    documentos: list[dict[str, Any]] = []
    if not base.is_dir():
        return documentos
    for ruta in sorted(base.glob("*.json")):
        try:
            with ruta.open("r", encoding="utf-8") as f:
                documentos.append(json.load(f))
        except (OSError, json.JSONDecodeError) as exc:
            LOG.warning("No se pudo leer %s: %s", ruta, exc)
    return documentos


def resumen_por_vacante(silver_dir: str | Path) -> dict[str, Any]:
    """Total y desglose de estados por vacante (vista de texto/CLI)."""
    documentos = _leer_documentos(silver_dir)
    por_vacante: dict[str, dict[str, Any]] = {}
    for doc in documentos:
        vacante = doc.get("vacante_id") or "Sin vacante"
        fila = por_vacante.setdefault(vacante, {"total": 0, "por_estado": Counter()})
        fila["total"] += 1
        fila["por_estado"][doc.get("estado_procesamiento") or "Sin estado"] += 1

    return {
        "total": len(documentos),
        "por_vacante": {
            vacante: {
                "total": fila["total"],
                "por_estado": dict(fila["por_estado"]),
            }
            for vacante, fila in sorted(por_vacante.items())
        },
    }


def _fecha_de(valor: Any) -> date | None:
    if not valor or not isinstance(valor, str):
        return None
    try:
        return datetime.fromisoformat(valor.replace("Z", "+00:00")).date()
    except ValueError:
        return None


def ultima_fecha_procesada(silver_dir: str | Path) -> date | None:
    """Fecha más reciente vista en silver (fecha_envio o fecha_ingesta)."""
    fechas: list[date] = []
    for doc in _leer_documentos(silver_dir):
        fecha = _fecha_de(doc.get("fecha_envio")) or _fecha_de(doc.get("fecha_ingesta"))
        if fecha is not None:
            fechas.append(fecha)
    return max(fechas) if fechas else None


def dias_desde_ultima(
    silver_dir: str | Path, hoy: date | None = None
) -> int | None:
    """Días a buscar hacia atrás para no perder correos (None si silver vacío)."""
    ultima = ultima_fecha_procesada(silver_dir)
    if ultima is None:
        return None
    referencia = hoy or date.today()
    return max((referencia - ultima).days + 1, 1)
