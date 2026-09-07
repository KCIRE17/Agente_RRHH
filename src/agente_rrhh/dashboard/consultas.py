"""Consultas del dashboard F3: lectura de gold y silver sin tocar la UI.

Toda función acepta rutas (``gold_dir`` / ``silver_dir``) para que la capa sea
independiente de Config y testeable sin arrancar Streamlit.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from ..core.config import (
    ESTADO_EVALUACION_REINTENTO,
    ESTADO_EVALUADO,
    ESTADO_FORMATO,
    ESTADO_ILEGIBLE,
    ESTADO_LISTO,
    ESTADO_REINTENTO,
)

LOG = logging.getLogger("agente_rrhh")

NOMBRE_RANKING = "ranking.json"
ESTADOS_COLOR = {
    "Alta": "#16a34a",
    "Media": "#d97706",
    "Baja": "#dc2626",
}
CLASIFICACION_ORDEN = {"Alta": 0, "Media": 1, "Baja": 2}

ESTADOS_AMIGABLES = {
    ESTADO_LISTO: "Pendiente de evaluación",
    ESTADO_EVALUADO: "Evaluado",
    ESTADO_ILEGIBLE: "Documento no legible",
    ESTADO_FORMATO: "Formato no permitido",
    ESTADO_REINTENTO: "En espera de nuevo intento",
    ESTADO_EVALUACION_REINTENTO: "Pendiente de re-evaluación",
}


def estado_amigable(estado: str) -> str:
    """Traduce el estado interno a una etiqueta comprensible para RRHH."""
    return ESTADOS_AMIGABLES.get(estado, estado or "Sin información")


def _leer_json(ruta: Path) -> dict[str, Any] | None:
    try:
        with ruta.open("r", encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError) as exc:
        LOG.warning("No se pudo leer %s: %s", ruta, exc)
        return None


def _vacio() -> dict[str, Any]:
    return {"candidatos": []}


def listar_vacantes_con_ranking(gold_dir: str | Path) -> list[dict[str, Any]]:
    """Devuelve las vacantes con evaluaciones en gold (carpeta + vacante_id)."""
    evaluacion = Path(gold_dir) / "evaluacion"
    vacantes: list[dict[str, Any]] = []
    if not evaluacion.is_dir():
        return vacantes
    for carpeta in sorted(evaluacion.iterdir()):
        if not carpeta.is_dir():
            continue
        ranking = _leer_json(carpeta / NOMBRE_RANKING) or _vacio()
        filas = ranking.get("candidatos") or []
        vacante_id = ranking.get("vacante_id") or _vacante_id_desde_slug(carpeta.name)
        total = len(filas)
        if total == 0:
            continue
        vacantes.append(
            {
                "carpeta": carpeta.name,
                "vacante_id": vacante_id,
                "total": total,
            }
        )
    return vacantes


def _vacante_id_desde_slug(slug: str) -> str:
    return " ".join(slug.split("_"))


def _slug(vacante_id: str) -> str:
    from ..core.vacantes import slug_vacante

    return slug_vacante(vacante_id)


def vacantes_evaluadas(gold_dir: str | Path) -> set[str]:
    """Carpetas de vacantes que ya tienen evaluaciones (gold)."""
    return {v["carpeta"] for v in listar_vacantes_con_ranking(gold_dir)}


def ranking_vacante(
    gold_dir: str | Path, carpeta: str
) -> tuple[str, list[dict[str, Any]]]:
    """Devuelve (vacante_id, filas del ranking) de una vacante (carpeta gold)."""
    directorio = Path(gold_dir) / "evaluacion" / carpeta
    ranking = _leer_json(directorio / NOMBRE_RANKING) or _vacio()
    filas = list(ranking.get("candidatos") or [])
    if not filas:
        filas = _recalcular_ranking_lectura(directorio)
    vacante_id = ranking.get("vacante_id") or (
        filas[0].get("vacante_id") if filas else _vacante_id_desde_slug(carpeta)
    )
    for pos, fila in enumerate(filas, start=1):
        fila["posicion"] = pos
    return vacante_id, filas


def _recalcular_ranking_lectura(directorio: Path) -> list[dict[str, Any]]:
    filas: list[dict[str, Any]] = []
    for ruta in sorted(directorio.glob("*.json")):
        if ruta.name == NOMBRE_RANKING:
            continue
        doc = _leer_json(ruta)
        if not doc or not isinstance(doc.get("match_score"), (int, float)):
            continue
        filas.append(
            {
                "vacante_id": doc.get("vacante_id"),
                "id_candidato": doc.get("id_candidato"),
                "nombre": doc.get("nombre_completo"),
                "email_remitente": doc.get("email_remitente"),
                "telefono": doc.get("telefono"),
                "match_score": round(float(doc["match_score"]), 2),
                "clasificacion": doc.get("clasificacion"),
                "fecha_evaluacion": doc.get("fecha_evaluacion"),
            }
        )
    filas.sort(key=lambda f: f["match_score"], reverse=True)
    return filas


def detalle_candidato(
    gold_dir: str | Path, silver_dir: str | Path, carpeta: str, id_candidato: str
) -> dict[str, Any] | None:
    """Gold del candidato unido con su CV estructurado (silver)."""
    ruta = Path(gold_dir) / "evaluacion" / carpeta / f"{id_candidato}.json"
    doc = _leer_json(ruta)
    if doc is None:
        return None
    silver = _buscar_silver(silver_dir, id_candidato)
    doc["silver"] = silver
    desglose = doc.get("desglose") or {}
    doc["puntos_por_bloque"] = {
        "Habilidades": (desglose.get("habilidades") or {}).get("puntos", 0),
        "Experiencia": (desglose.get("experiencia") or {}).get("puntos", 0),
        "Formación": (desglose.get("formacion") or {}).get("puntos", 0),
    }
    return doc


def _buscar_silver(
    silver_dir: str | Path, id_candidato: str
) -> dict[str, Any] | None:
    from ..core.json_store import JsonStore

    store = JsonStore(silver_dir)
    for doc in store.candidatos():
        if doc.get("id_candidato") == id_candidato:
            return doc
    return None


def resumen_ingesta(
    silver_dir: str | Path, gold_dir: str | Path | None = None
) -> dict[str, Any]:
    """Conteos de silver por estado y por vacante (vista 'Ingesta').

    El número de "evaluados" se deriva de gold (ranking), no del estado silver,
    porque F2 no muta silver al evaluar.
    """
    from ..core.json_store import JsonStore

    docs = JsonStore(silver_dir).candidatos()
    evaluados_por_slug: dict[str, int] = {}
    if gold_dir is not None:
        for v in listar_vacantes_con_ranking(gold_dir):
            _, filas = ranking_vacante(gold_dir, v["carpeta"])
            evaluados_por_slug[v["carpeta"]] = len(filas)

    por_estado: dict[str, int] = {}
    por_vacante: dict[str, dict[str, Any]] = {}
    for doc in docs:
        estado = doc.get("estado_procesamiento") or "Sin estado"
        etiqueta = estado_amigable(estado)
        por_estado[etiqueta] = por_estado.get(etiqueta, 0) + 1
        vacante = doc.get("vacante_id") or "Sin vacante"
        fila = por_vacante.setdefault(
            vacante,
            {"total": 0, "evaluados": 0, "listos": 0, "errores": 0, "reintentos": 0},
        )
        fila["total"] += 1
        if estado in ("Error: Archivo Ilegible", "Error: Formato No Permitido"):
            fila["errores"] += 1
        elif "Reintento" in estado:
            fila["reintentos"] += 1

    if gold_dir is not None:
        for vacante, fila in por_vacante.items():
            slug = _slug(vacante)
            fila["evaluados"] = evaluados_por_slug.get(slug, 0)
            fila["listos"] = max(
                fila["total"] - fila["evaluados"] - fila["errores"] - fila["reintentos"],
                0,
            )
    return {
        "total_silver": len(docs),
        "por_estado": por_estado,
        "por_vacante": por_vacante,
    }


def sugerencia_clasificacion(clasificacion: str) -> dict[str, Any]:
    """Regla de negocio visual: qué hacer con el candidato según su clase."""
    sugerencias = {
        "Alta": {
            "titulo": "Pase a fase técnica",
            "descripcion": (
                "Alta compatibilidad con la vacante. Avanzar a entrevista o "
                "prueba técnica."
            ),
            "nivel": 2,
        },
        "Media": {
            "titulo": "Revisión manual",
            "descripcion": (
                "Compatibilidad media. Revisar fortalezas y brechas antes de "
                "decidir el siguiente paso."
            ),
            "nivel": 1,
        },
        "Baja": {
            "titulo": "No avanza",
            "descripcion": (
                "Baja compatibilidad con la vacante. No avanzar en el proceso."
            ),
            "nivel": 0,
        },
    }
    return sugerencias.get(clasificacion, sugerencias["Baja"])