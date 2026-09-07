#!/usr/bin/env python
"""Punto de entrada del proyecto (Fases 1, 2 y 3).

Uso:
    uv run python main.py                 # lote real (IMAP + Gemini + JSON silver)
    uv run python main.py --dry-run       # prueba sin gastar cuota ni guardar datos
    uv run python main.py --max 5         # limita a 5 correos
    uv run python main.py --programar     # programa el lote diario a las 18:00
    uv run python main.py limpiar         # purga bronze (retención de .env)
    uv run python main.py limpiar --dias 7  # purga bronze de más de 7 días
    uv run python main.py evaluar [--vacante X] [--dry-run]
    uv run python main.py evaluar --dry-run  --vacante "ANALISTA DE DATOS"  # simula
    uv run python main.py dashboard [--port 8501]  # panel Streamlit (F3)
"""

from __future__ import annotations

import argparse
import logging
import subprocess
import sys
import time
from pathlib import Path

from src.agente_rrhh.core.config import Config
from src.agente_rrhh.core.logging_setup import configurar_logging
from src.agente_rrhh.core.raw_store import RawStore
from src.agente_rrhh.evaluation.pipeline_evaluacion import PipelineEvaluacion
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


def ejecutar_evaluacion(
    cfg: Config, vacante: str | None, dry_run: bool
) -> int:
    if not cfg.groq_api_key and not dry_run:
        LOG.warning(
            "GROQ_API_KEY vacía en .env: sin la clave real solo se puede "
            "usar el modo --dry-run."
        )

    pipeline = PipelineEvaluacion(cfg, dry_run=dry_run, vacante=vacante)
    try:
        pipeline.ejecutar()
    except Exception as exc:
        LOG.exception("Error durante la evaluacion: %s", exc)
        return 1
    finally:
        pipeline.cerrar()
    return 0


def ejecutar_dashboard(puerto: int) -> int:
    app = Path(__file__).parent / "src/agente_rrhh/dashboard/app.py"
    LOG.info("Arrancando dashboard en http://localhost:%d (Ctrl+C para salir).", puerto)
    cmd = [sys.executable, "-m", "streamlit", "run", str(app), "--server.port", str(puerto)]
    return subprocess.run(cmd, cwd=Path(__file__).parent).returncode


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Ingesta (IMAP -> silver), evaluacion (silver -> gold) y "
        "dashboard (Streamlit)."
    )
    parser.add_argument(
        "comando",
        nargs="?",
        choices=["limpiar", "evaluar", "dashboard"],
        help="'limpiar' purga bronze; 'evaluar' corre el Match Score (F2); "
        "'dashboard' abre el panel F3.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Simula el flujo sin llamar a la IA ni guardar en silver/gold.",
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
        "--vacante",
        type=str,
        default=None,
        help="Con 'evaluar': filtra los candidatos de una sola vacante.",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8501,
        help="Con 'dashboard': puerto del panel Streamlit (default 8501).",
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

    if args.comando == "evaluar":
        return ejecutar_evaluacion(cfg, args.vacante, args.dry_run)

    if args.comando == "dashboard":
        return ejecutar_dashboard(args.port)

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