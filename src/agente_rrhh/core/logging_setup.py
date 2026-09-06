"""Configuración del sistema de logging (consola + archivo)."""

from __future__ import annotations

import logging
import os
import sys


def configurar_logging(nivel: int = logging.INFO) -> None:
    """Configura logs en consola y en logs/ingesta.log."""
    os.makedirs("logs", exist_ok=True)
    formato = "%(asctime)s | %(levelname)-7s | %(message)s"
    handler_consola = logging.StreamHandler(sys.stdout)
    handler_archivo = logging.FileHandler(
        os.path.join("logs", "ingesta.log"), encoding="utf-8"
    )
    logging.basicConfig(
        level=nivel,
        format=formato,
        handlers=[handler_consola, handler_archivo],
    )