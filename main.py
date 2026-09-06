#!/usr/bin/env python
"""Punto de entrada del Módulo de Ingesta (Fase 1).

Uso:
    uv run python main.py                 # lote real (IMAP + Gemini + JSON silver)
    uv run python main.py --dry-run       # prueba sin gastar cuota ni guardar datos
    uv run python main.py --max 5         # limita a 5 correos
    uv run python main.py --programar     # programa el lote diario a las 18:00
    uv run python main.py limpiar         # purga bronze (retención de .env)
    uv run python main.py limpiar --dias 7  # purga bronze de más de 7 días
"""

from __future__ import annotations

import argparse
import logging
import time

from src.agente_rrhh.core.config import Config
from src.agente_rrhh.core.logging_setup import configurar_logging
from src.agente_rrhh.core.raw_store import RawStore
from src.agente_rrhh.ingestion.imap_client import ImapClient
from src.agente_rrhh.ingestion.pipeline import PipelineIngesta

LOG = logging.getLogger("agente_rrhh")


def ejecutar_lote(cfg: Config, dry_run: bool, max_mensajes: int | None) -> int:
    faltantes = cfg.validar()
    if faltantes:
        LOG.error("Faltan variables requeridas en .env: %s", ", ".join(faltantes))
        return 1

    if not cfg.gemini_api_key and not dry_run:
        LOG.warning(
            "GEMINI_API_KEY vacía en .env: los candidatos quedarán en "
            "'Pendiente: Reintento IA'."
        )

    pipeline = None
    imap = None
    try:
        pipeline = PipelineIngesta(cfg, dry_run=dry_run, max_mensajes=max_mensajes)
        imap = ImapClient(cfg).conectar()
        pipeline.ejecutar(imap)
    except Exception as exc:
        LOG.exception("Error durante el lote: %s", exc)
        return 1
    finally:
        if imap is not None:
            imap.cerrar()
        if pipeline is not None:
            pipeline.cerrar()
    return 0


def ejecutar_limpieza(cfg: Config, dias: int | None) -> int:
    dias_efectivo = dias if dias is not None and dias > 0 else cfg.retencion_dias
    raw = RawStore(cfg.bronze_dir)

    deduplicadas = raw.deduplicar()
    borrados = raw.limpiar_por_dias(dias_efectivo)
    raw.limpiar_carpetas_vacias()

    for copia in deduplicadas:
        LOG.info("Deduplicada copia repetida: %s", copia)
    for archivo in borrados:
        LOG.info("Purga (más de %d días): %s", dias_efectivo, archivo)
    LOG.info(
        "Limpieza completada: %d copias duplicadas y %d archivos viejos eliminados.",
        len(deduplicadas),
        len(borrados),
    )
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Ingesta de postulaciones desde Gmail (IMAP) a la capa silver."
    )
    parser.add_argument(
        "comando",
        nargs="?",
        choices=["limpiar"],
        help="'limpiar' purga bronze (archivos originales viejos y copias duplicadas).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Simula el flujo sin llamar a Gemini ni guardar en silver.",
    )
    parser.add_argument(
        "--max",
        type=int,
        default=None,
        help="Procesa como máximo N correos en este lote.",
    )
    parser.add_argument(
        "--dias",
        type=int,
        default=None,
        help="Con 'limpiar': retención en días (default RAWDATA_RETENCION_DIAS).",
    )
    parser.add_argument(
        "--programar",
        action="store_true",
        help="Programa la ejecución diaria a la hora HORA_INGESTA.",
    )
    parser.add_argument(
        "--verbose", action="store_true", help="Logs en nivel DEBUG."
    )
    args = parser.parse_args()

    configurar_logging(logging.DEBUG if args.verbose else logging.INFO)
    cfg = Config.desde_env()

    if args.comando == "limpiar":
        return ejecutar_limpieza(cfg, args.dias)

    if args.programar:
        import schedule

        LOG.info(
            "Programando lote diario a las %s. Ctrl+C para salir.",
            cfg.hora_ingesta,
        )
        schedule.every().day.at(cfg.hora_ingesta).do(
            ejecutar_lote, cfg, args.dry_run, args.max
        )
        while True:
            schedule.run_pending()
            time.sleep(60)

    return ejecutar_lote(cfg, args.dry_run, args.max)


if __name__ == "__main__":
    raise SystemExit(main())