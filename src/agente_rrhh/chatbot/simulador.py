"""Simulador de pesos del match score (sin IA, costo $0).

Parte del ``desglose`` ya guardado en gold (parcial 0-100 por bloque) y
recalcula el puntaje con pesos alternativos. Respetando las reglas de F2:
clamp 0-100 y umbrales Alta >= 80, Media >= 50, Baja < 50.
"""

from __future__ import annotations

from typing import Any

from . import datos

BLOQUES = ("habilidades", "experiencia", "formacion")
PESOS_DEFAULT = {"habilidades": 0.5, "experiencia": 0.3, "formacion": 0.2}


def normalizar_pesos(pesos: dict[str, Any] | None) -> dict[str, float]:
    p = {
        "habilidades": float((pesos or {}).get("habilidades", 0) or 0),
        "experiencia": float((pesos or {}).get("experiencia", 0) or 0),
        "formacion": float((pesos or {}).get("formacion", 0) or 0),
    }
    total = sum(p.values())
    if total <= 0:
        return dict(PESOS_DEFAULT)
    return {k: v / total for k, v in p.items()}


def clasificar(nuevo: float) -> str:
    if nuevo >= 80:
        return "Alta"
    if nuevo >= 50:
        return "Media"
    return "Baja"


def simular(
    cfg: Any, carpeta: str | None = None, pesos: dict[str, Any] | None = None
) -> dict[str, Any]:
    """Re-ranking de los evaluados con pesos alternativos."""
    p = normalizar_pesos(pesos)
    docs = datos.docs_evaluados(cfg)
    if carpeta:
        docs = [d for d in docs if d["carpeta"] == carpeta]

    resultados = []
    for e in docs:
        desglose = e["doc"].get("desglose") or {}
        parciales = {
            bloque: (
                (desglose.get(bloque) or {}).get("parcial", 0)
                if desglose and isinstance(desglose.get(bloque), dict)
                else 0
            )
            for bloque in BLOQUES
        }
        original = float(e["fila"].get("match_score", 0) or 0)
        nuevo = (
            parciales["habilidades"] * p["habilidades"]
            + parciales["experiencia"] * p["experiencia"]
            + parciales["formacion"] * p["formacion"]
        )
        nuevo = max(0.0, min(100.0, round(nuevo, 2)))
        resultados.append(
            {
                "id_candidato": e["fila"]["id_candidato"],
                "nombre": e["fila"]["nombre"],
                "vacante": e["carpeta"],
                "parciales": parciales,
                "original": original,
                "nuevo": nuevo,
                "delta": round(nuevo - original, 2),
                "clasificacion_original": e["fila"].get("clasificacion", ""),
                "clasificacion": clasificar(nuevo),
            }
        )
    resultados.sort(key=lambda r: r["nuevo"], reverse=True)
    return {"pesos": p, "resultados": resultados}