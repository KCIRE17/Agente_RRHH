"""Bitacora de uso de tokens y calculo de costos estimados.

Cada llamada a la IA (chat F4) se registra en
``data/gold/costo/uso_chat.jsonl`` (lineas JSON, append atomico). El costo se
estima con tarifas configurables en ``config/tarifas.json``. En modo offline
(0 llamadas) la bitacora queda vacia y el costo total es $0.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

LOG = logging.getLogger("agente_rrhh")


def _ahora_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def leer_tarifas(ruta: str | Path) -> dict[str, Any]:
    """Tarifas $/1M tokens por modelo (config/tarifas.json)."""
    return _leer_tarifas(ruta)


def _leer_tarifas(ruta: str | Path) -> dict[str, Any]:
    try:
        with Path(ruta).open("r", encoding="utf-8") as f:
            datos = json.load(f)
        return datos.get("tarifas") or {}
    except (OSError, json.JSONDecodeError) as exc:
        LOG.warning("No se pudieron cargar tarifas %s: %s", ruta, exc)
        return {}


def calcular_costo(
    prompt_tokens: int,
    completado_tokens: int,
    modelo: str,
    ruta_tarifas: str | Path = "config/tarifas.json",
) -> float:
    """Costo estimado en USD (tarifas $/1M tokens) sumando prompt+respuesta."""
    tarifas = _leer_tarifas(ruta_tarifas)
    precio = tarifas.get(modelo) or tarifas.get("defecto") or {"entrada": 0.0, "salida": 0.0}
    entrada = float(precio.get("entrada", 0.0))
    salida = float(precio.get("salida", 0.0))
    costo = (prompt_tokens / 1_000_000 * entrada) + (
        completado_tokens / 1_000_000 * salida
    )
    return round(costo, 8)


def registrar_uso(
    ruta_jsonl: str | Path,
    fase: str,
    proveedor: str,
    modelo: str,
    prompt_tokens: int,
    completado_tokens: int,
    ruta_tarifas: str | Path = "config/tarifas.json",
    **extra: Any,
) -> dict[str, Any]:
    """Registra una llamada en la bitacora jsonl y devuelve el registro."""
    registro = {
        "fecha": _ahora_iso(),
        "fase": fase,
        "proveedor": proveedor,
        "modelo": modelo,
        "prompt_tokens": int(prompt_tokens),
        "completado_tokens": int(completado_tokens),
        "total_tokens": int(prompt_tokens) + int(completado_tokens),
        "costo_usd": calcular_costo(
            int(prompt_tokens), int(completado_tokens), modelo, ruta_tarifas
        ),
    }
    registro.update(extra)
    ruta = Path(ruta_jsonl)
    ruta.parent.mkdir(parents=True, exist_ok=True)
    try:
        with ruta.open("a", encoding="utf-8") as f:
            f.write(json.dumps(registro, ensure_ascii=False) + "\n")
    except OSError as exc:
        LOG.warning("No se pudo registrar uso en %s: %s", ruta, exc)
    return registro


def leer_usos(ruta_jsonl: str | Path) -> list[dict[str, Any]]:
    """Lee todas las llamadas registradas en la bitacora jsonl."""
    ruta = Path(ruta_jsonl)
    usos: list[dict[str, Any]] = []
    if not ruta.is_file():
        return usos
    try:
        with ruta.open("r", encoding="utf-8") as f:
            for linea in f:
                linea = linea.strip()
                if not linea:
                    continue
                try:
                    usos.append(json.loads(linea))
                except json.JSONDecodeError:
                    LOG.warning("Linea invalida en %s: %r", ruta, linea[:80])
    except OSError as exc:
        LOG.warning("No se pudo leer la bitacora %s: %s", ruta, exc)
    return usos


def resumir(usos: list[dict[str, Any]]) -> dict[str, Any]:
    """Agrega tokens y costo de una lista de registros."""
    total = sum(u.get("total_tokens", 0) or 0 for u in usos)
    costo = sum(u.get("costo_usd", 0.0) or 0.0 for u in usos)
    llamadas = len(usos)
    return {
        "llamadas": llamadas,
        "total_tokens": total,
        "costo_usd": round(costo, 8),
    }