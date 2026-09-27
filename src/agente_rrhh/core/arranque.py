"""Arranque de un clic para entregar el proyecto en otra laptop.

Reune lo que hace falta para que el sistema quede de pie sin pasos manuales:
preparar el ``.env``, sembrar los datos ficticios versionados en ``data_demo/``,
reservar puertos libres, abrir el navegador y reportar que fases quedan
operativas con las credenciales actuales.

Vive en ``core/`` porque el entregable lo usan el comando ``demo`` de
``main.py`` y los lanzadores ``INICIAR.bat`` / ``iniciar.sh``.
"""

from __future__ import annotations

import logging
import shutil
import socket
import webbrowser
from pathlib import Path
from typing import Any, NamedTuple

from .config import ESTADO_LISTO, Config
from .json_store import JsonStore

LOG = logging.getLogger("agente_rrhh")

# Carpeta de datos ficticios versionados (30+ candidatos) que se siembran al
# arrancar: es la misma que usa el deploy de Vercel, asi que la demo local y la
# nube muestran exactamente los mismos datos.
DIR_DEMO = "data_demo"

# Subcarpetas del medallion que se copian de data_demo/ a data/.
SUBCARPETAS_SEMILLA = ("silver", "gold")

# Rango de puertos probed para F3 (dashboard) y F4 (chatbot).
PUERTO_INICIAL_DASHBOARD = 8501
PUERTO_INICIAL_CHAT = 8510
PUERTO_MAXIMO = 8599


class FilaDiagnostico(NamedTuple):
    """Fila del reporte de estado que ve el evaluador al arrancar."""

    fase: str
    listo: bool
    detalle: str


def asegurar_env(raiz: Path) -> tuple[Path, bool]:
    """Crea ``.env`` desde ``.env.example`` si no existe.

    Devuelve ``(ruta, creado)``. Nunca sobreescribe un ``.env`` real: las
    credenciales del responsable se respetan tal cual.
    """
    destino = raiz / ".env"
    if destino.exists():
        return destino, False
    plantilla = raiz / ".env.example"
    if not plantilla.exists():
        LOG.warning("No se encontro .env.example; el .env quedara sin crear.")
        return destino, False
    shutil.copyfile(plantilla, destino)
    LOG.info("Se creo .env a partir de .env.example (sin credenciales).")
    return destino, True


def sembrar_datos_demo(raiz: Path, destino: Path) -> bool:
    """Copia los datos ficticios de ``data_demo/`` a ``destino`` (default ``data/``).

    Solo siembra si el destino no tiene candidatos en ``silver/``: sobre datos
    reales no se toca nada. Devuelve ``True`` si sembró.
    """
    origen = raiz / DIR_DEMO
    if not origen.is_dir():
        LOG.warning("No existe %s: el panel arrancara sin datos.", DIR_DEMO)
        return False

    if JsonStore(destino / "silver").candidatos():
        return False

    for sub in SUBCARPETAS_SEMILLA:
        fuente = origen / sub
        if not fuente.is_dir():
            continue
        shutil.copytree(fuente, destino / sub, dirs_exist_ok=True)
        LOG.info("Datos demo sembrados en %s (%s).", destino / sub, DIR_DEMO)
    return True


def puerto_libre(puerto: int, host: str = "127.0.0.1", evitar: set[int] | None = None) -> int:
    """Primer puerto libre desde ``puerto``, saltando los ya reservados.

    Evita choques cuando la laptop ya tiene otro servicio en 8501/8510.
    """
    descartados = evitar or set()
    for candidato in range(puerto, PUERTO_MAXIMO + 1):
        if candidato in descartados:
            continue
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                sock.bind((host, candidato))
            except OSError:
                continue
        return candidato
    raise OSError(f"No hay puertos libres entre {puerto} y {PUERTO_MAXIMO}.")


def abrir_navegador(url: str) -> bool:
    """Abre el navegador; si falla (entorno sin GUI) solo avisa por log."""
    try:
        return bool(webbrowser.open(url))
    except Exception as exc:  # pragma: no cover - depende del escritorio
        LOG.warning("No se pudo abrir el navegador: %s", exc)
        return False


def _contar_evaluados(destino: Path) -> int:
    """Cuentas las evaluaciones de gold, sin los ``ranking.json`` derivados."""
    evaluacion = destino / "gold" / "evaluacion"
    if not evaluacion.is_dir():
        return 0
    return sum(
        1
        for ruta in evaluacion.rglob("*.json")
        if ruta.name != "ranking.json"
    )


def diagnostico(cfg: Config, raiz: Path) -> list[FilaDiagnostico]:
    """Reporta que fases quedan operativas con el ``.env`` actual.

    Sirve de primer pantallazo para el evaluador: las UIs (F3/F4) siempre
    levantan con los datos demo; F1/F2 con IA real dependen de las claves.
    """
    destino = Path(cfg.data_dir)
    if not destino.is_absolute():
        destino = raiz / destino
    listos = len(JsonStore(destino / "silver").candidatos(estado=ESTADO_LISTO))
    evaluados = _contar_evaluados(destino)

    faltantes_f1 = cfg.validar()
    if faltantes_f1:
        detalle_f1 = (
            "Falta " + ", ".join(faltantes_f1) + " en .env: la ingesta no puede ejecutarse"
        )
        f1 = False
    elif cfg.gemini_api_key:
        detalle_f1 = "IMAP + Gemini listos (extracción con IA real)"
        f1 = True
    else:
        detalle_f1 = (
            "IMAP listo; sin GEMINI_API_KEY los candidatos quedan en "
            "'Pendiente: Reintento IA'"
        )
        f1 = False

    f2 = bool(cfg.groq_api_key)
    detalle_f2 = (
        f"Groq listo, {listos} candidato(s) en 'Listo para Evaluación'"
        if f2
        else f"Sin GROQ_API_KEY: {listos} candidato(s) esperando, corre con --dry-run"
    )

    filas = [
        FilaDiagnostico("F1 Ingesta (IMAP + Gemini)", f1, detalle_f1),
        FilaDiagnostico("F2 Evaluación (Groq)", f2, detalle_f2),
        FilaDiagnostico(
            "F3 Dashboard (Streamlit)",
            True,
            f"{evaluados} evaluación(es) cargada(s) desde {cfg.data_dir}/gold",
        ),
        FilaDiagnostico(
            "F4 Chatbot (web)",
            True,
            "100 % en código, costo $0"
            + ("" if cfg.proveedor_chat else " (narrativa IA offline)")
            + ("" if not cfg.login_habilitado else ", con login"),
        ),
    ]
    return filas


def imprimir_diagnostico(filas: list[FilaDiagnostico], stream: Any) -> None:
    """Pinta el reporte de estado en la consola (sin dependencias externas)."""
    ancho = max(len(f.fase) for f in filas) + 2
    print("", file=stream)
    print("  ESTADO DEL SISTEMA", file=stream)
    print("  " + "-" * (ancho + 26), file=stream)
    for fila in filas:
        marca = "OK  " if fila.listo else "AVISO"
        print(f"  [{marca}] {fila.fase:<{ancho}} {fila.detalle}", file=stream)
    print("", file=stream)
