"""Acceso a datos (silver/gold) para el chatbot F4, sin tocar la UI.

Reutiliza ``dashboard.consultas`` (capas ya existentes) para no duplicar
logica de lectura del medallion.
"""

from __future__ import annotations

import re
from typing import Any

from ..dashboard import consultas


def vacantes(cfg: Any) -> list[dict[str, Any]]:
    return consultas.listar_vacantes_con_ranking(cfg.gold_dir)


def ranking(cfg: Any, carpeta: str) -> tuple[str, list[dict[str, Any]]]:
    return consultas.ranking_vacante(cfg.gold_dir, carpeta)


def detalle(cfg: Any, carpeta: str, candidato_id: str) -> dict[str, Any] | None:
    return consultas.detalle_candidato(
        cfg.gold_dir, cfg.silver_dir, carpeta, candidato_id
    )


def docs_evaluados(cfg: Any) -> list[dict[str, Any]]:
    """Todas las evaluaciones (gold) unidas con su silver y fila de ranking."""
    resultados: list[dict[str, Any]] = []
    for v in vacantes(cfg):
        _, filas = ranking(cfg, v["carpeta"])
        for fila in filas:
            doc = detalle(cfg, v["carpeta"], fila["id_candidato"])
            if doc is not None:
                resultados.append({"carpeta": v["carpeta"], "fila": fila, "doc": doc})
    return resultados


def resumen_ingesta(cfg: Any) -> dict[str, Any]:
    return consultas.resumen_ingesta(cfg.silver_dir, cfg.gold_dir)


def _estructurado(doc: dict[str, Any]) -> dict[str, Any]:
    return (doc.get("silver") or {}).get("datos_json", {}).get(
        "datos_estructurados", {}
    ) or {}


def habilidades(doc: dict[str, Any]) -> list[str]:
    return list(_estructurado(doc).get("habilidades") or [])


def experiencia_anos(doc: dict[str, Any]) -> float:
    items = _estructurado(doc).get("experiencia_laboral") or []
    total = sum(float(item.get("duracion_anos", 0) or 0) for item in items)
    return round(total, 1)


def formaciones(doc: dict[str, Any]) -> list[str]:
    items = _estructurado(doc).get("formacion_academica") or []
    return [
        f"{i.get('grado', '')} en {i.get('carrera', '')}".strip(" en ")
        for i in items
    ]


def dominio(doc: dict[str, Any]) -> str:
    silver = doc.get("silver") or {}
    dom = ((silver.get("remitente_metadatos") or {}).get("dominio")) or ""
    if not dom:
        m = re.search(r"@([A-Za-z0-9.\-]+)", doc.get("email_remitente") or "")
        dom = m.group(1) if m else ""
    return dom.lower().lstrip(".")


def tokens_f2(cfg: Any) -> dict[str, Any]:
    """Tokens registrados por la fase 2 (uso_tokens de cada doc gold)."""
    prompt_total = completado_total = 0
    n = 0
    for e in docs_evaluados(cfg):
        uso = e["doc"].get("uso_tokens") or {}
        prompt_total += int(uso.get("prompt", 0) or 0)
        completado_total += int(uso.get("completado", 0) or 0)
        n += 1
    return {
        "candidatos": n,
        "prompt_tokens": prompt_total,
        "completado_tokens": completado_total,
        "total_tokens": prompt_total + completado_total,
    }