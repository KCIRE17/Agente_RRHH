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
    uv run python main.py chat [--port 8510]       # chatbot F4 (app web local)
    uv run python main.py demo                     # entrega de un clic: F3 + F4
"""

from __future__ import annotations

import argparse
import importlib.util
import logging
import subprocess
import sys
import threading
import time
from pathlib import Path

from src.agente_rrhh.core import arranque
from src.agente_rrhh.core.config import Config
from src.agente_rrhh.core.logging_setup import configurar_logging
from src.agente_rrhh.core.raw_store import RawStore
from src.agente_rrhh.evaluation.pipeline_evaluacion import PipelineEvaluacion
from src.agente_rrhh.ingestion.imap_client import ImapClient
from src.agente_rrhh.ingestion.pipeline import PipelineIngesta

LOG = logging.getLogger("agente_rrhh")
RAIZ = Path(__file__).resolve().parent

# Espera a que el dashboard de Streamlit levante antes de abrir el navegador.
_ESPERA_NAVEGADOR_SEG = 3.0


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
    cfg: Config, vacante: str | None, dry_run: bool, re_evaluar: bool = False
) -> int:
    if not cfg.groq_api_key and not dry_run:
        LOG.warning(
            "GROQ_API_KEY vacía en .env: sin la clave real solo se puede "
            "usar el modo --dry-run."
        )

    pipeline = PipelineEvaluacion(
        cfg, dry_run=dry_run, vacante=vacante, re_evaluar=re_evaluar
    )
    try:
        pipeline.ejecutar()
    except Exception as exc:
        LOG.exception("Error durante la evaluacion: %s", exc)
        return 1
    finally:
        pipeline.cerrar()
    return 0


def ejecutar_dashboard(puerto: int) -> int:
    app = RAIZ / "src/agente_rrhh/dashboard/app.py"
    LOG.info("Arrancando dashboard en http://localhost:%d (Ctrl+C para salir).", puerto)
    cmd = [sys.executable, "-m", "streamlit", "run", str(app), "--server.port", str(puerto)]
    return subprocess.run(cmd, cwd=RAIZ).returncode


def ejecutar_chat(puerto: int) -> int:
    import uvicorn

    from src.agente_rrhh.chatbot.api import crear_app

    app = crear_app(Config.desde_env())
    LOG.info("Arrancando chatbot F4 en http://127.0.0.1:%d (Ctrl+C para salir).", puerto)
    return uvicorn.run(app, host="127.0.0.1", port=puerto, log_level="warning")


def _lanzar_dashboard(puerto: int) -> subprocess.Popen[bytes] | None:
    """Levanta F3 como subproceso. Devuelve ``None`` si Streamlit no esta instalado."""
    if importlib.util.find_spec("streamlit") is None:
        LOG.warning(
            "Streamlit no esta instalado: se omite el dashboard F3. "
            "Instala con 'pip install -r requirements-full.txt' para incluirlo."
        )
        return None
    app = RAIZ / "src/agente_rrhh/dashboard/app.py"
    cmd = [
        sys.executable,
        "-m",
        "streamlit",
        "run",
        str(app),
        "--server.port",
        str(puerto),
        # Solo red local: el panel muestra datos personales de candidatos.
        "--server.address",
        "127.0.0.1",
        # El navegador lo abre el propio comando demo, no Streamlit.
        "--server.headless",
        "true",
        "--browser.gatherUsageStats",
        "false",
    ]
    LOG.info("Dashboard F3: http://127.0.0.1:%d", puerto)
    return subprocess.Popen(cmd, cwd=RAIZ)


def ejecutar_demo(
    puerto_dashboard: int | None,
    puerto_chat: int | None,
    abrir: bool,
) -> int:
    """Entrega de un clic: siembra datos demo, reporta estado y levanta F3 + F4.

    Es el comando que ejecutan ``INICIAR.bat`` / ``iniciar.sh``: deja las dos
    interfaces abiertas en el navegador sin pasos manuales y sin tocar claves.
    """
    import uvicorn

    from src.agente_rrhh.chatbot.api import crear_app

    arranque.asegurar_env(RAIZ)
    cfg = Config.desde_env()
    destino = Path(cfg.data_dir)
    if not destino.is_absolute():
        destino = RAIZ / destino
    if not arranque.sembrar_datos_demo(RAIZ, destino):
        LOG.info("Se conserva la data actual en %s.", destino)

    puerto_f3 = arranque.puerto_libre(
        puerto_dashboard or arranque.PUERTO_INICIAL_DASHBOARD
    )
    puerto_f4 = arranque.puerto_libre(
        puerto_chat or arranque.PUERTO_INICIAL_CHAT, evitar={puerto_f3}
    )

    arranque.imprimir_diagnostico(arranque.diagnostico(cfg, RAIZ), sys.stdout)

    proceso = _lanzar_dashboard(puerto_f3)
    print(f"  Chatbot F4  : http://127.0.0.1:{puerto_f4}", file=sys.stdout)
    if proceso is not None:
        print(f"  Dashboard F3 : http://127.0.0.1:{puerto_f3}", file=sys.stdout)
    print("  Cerrar esta ventana o pulsar Ctrl+C para detener.\n", file=sys.stdout)

    if abrir:
        url_chat = f"http://127.0.0.1:{puerto_f4}"
        threading.Timer(
            _ESPERA_NAVEGADOR_SEG, lambda: arranque.abrir_navegador(url_chat)
        ).start()

    try:
        uvicorn.run(
            crear_app(cfg), host="127.0.0.1", port=puerto_f4, log_level="warning"
        )
    except KeyboardInterrupt:
        print("\nDeteniendo el chatbot F4.", file=sys.stdout)
    finally:
        if proceso is not None and proceso.poll() is None:
            proceso.terminate()
            try:
                proceso.wait(timeout=10)
            except subprocess.TimeoutExpired:  # pragma: no cover - cierre forzado
                proceso.kill()
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Ingesta (IMAP -> silver), evaluacion (silver -> gold), "
        "dashboard (Streamlit) y chatbot (FastAPI)."
    )
    parser.add_argument(
        "comando",
        nargs="?",
        choices=["limpiar", "evaluar", "dashboard", "chat", "demo"],
        help="'limpiar' purga bronze; 'evaluar' corre el Match Score (F2); "
        "'dashboard' abre el panel F3; 'chat' abre el asistente web F4; "
        "'demo' deja F3 + F4 listos en el navegador (entrega de un clic).",
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
        "--re-evaluar",
        action="store_true",
        help="Con 'evaluar': vuelve a evaluar aunque ya exista evaluación en "
        "gold (por defecto se omiten, para no gastar cuota).",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=None,
        help="Con 'dashboard', 'chat' o 'demo': puerto de la interfaz "
        "(default 8501 para F3 y 8510 para F4).",
    )
    parser.add_argument(
        "--port-dashboard",
        type=int,
        default=None,
        help="Solo con 'demo': puerto de F3 (default 8501).",
    )
    parser.add_argument(
        "--sin-navegador",
        action="store_true",
        help="Con 'demo': no abre el navegador automáticamente.",
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
        return ejecutar_evaluacion(
            cfg, args.vacante, args.dry_run, args.re_evaluar
        )

    if args.comando == "dashboard":
        return ejecutar_dashboard(args.port or arranque.PUERTO_INICIAL_DASHBOARD)

    if args.comando == "chat":
        return ejecutar_chat(args.port or arranque.PUERTO_INICIAL_CHAT)

    if args.comando == "demo":
        return ejecutar_demo(args.port_dashboard, args.port, not args.sin_navegador)

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