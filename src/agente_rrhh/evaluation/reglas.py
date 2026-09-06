"""Reglas de negocio del Match Score: ponderacion y clasificacion.

La IA propone el desglose parcial; el puntaje final y la clasificacion se
computan en codigo (deterministas) para que los pesos 50/30/20 siempre sumen
100 % y los umbrales sean estables.
"""

from __future__ import annotations

from typing import Any

PESOS: dict[str, float] = {
    "habilidades": 0.5,
    "experiencia": 0.3,
    "formacion": 0.2,
}

UMBRAL_ALTA = 80
UMBRAL_MEDIA = 50

CLASIFICACION_ALTA = "Alta"
CLASIFICACION_MEDIA = "Media"
CLASIFICACION_BAJA = "Baja"


def normalizar_score(valor: Any) -> int:
    """Clampa un valor a 0-100 (entero), tolerando None/texto."""
    if valor is None:
        return 0
    try:
        numero = float(valor)
    except (TypeError, ValueError):
        return 0
    return max(0, min(100, int(round(numero))))


def clasificar(score: int) -> str:
    if score >= UMBRAL_ALTA:
        return CLASIFICACION_ALTA
    if score >= UMBRAL_MEDIA:
        return CLASIFICACION_MEDIA
    return CLASIFICACION_BAJA


def componer_puntaje(datos_ia: dict[str, Any]) -> tuple[dict[str, Any], int]:
    """Devuelve (desglose, match_score) a partir de la respuesta de la IA.

    - Si la IA entrego los tres parciales, se recomponen los puntos ponderados
      y el score = suma de esos puntos (garantiza los pesos 50/30/20).
    - Si no, se usa el `match_score` que envio la IA, clampeado a 0-100.
    """
    raw = datos_ia.get("desglose") or {}
    if all(k in raw for k in PESOS):
        parciales = {k: normalizar_score(raw.get(k)) for k in PESOS}
        desglose = {
            k: {
                "peso": PESOS[k],
                "parcial": parciales[k],
                "puntos": round(parciales[k] * PESOS[k]),
            }
            for k in PESOS
        }
        return desglose, sum(d["puntos"] for d in desglose.values())

    return {}, normalizar_score(datos_ia.get("match_score", 0))