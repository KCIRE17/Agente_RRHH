"""Reintentos con backoff exponencial (util compartido, sin dependencias).

Se usa en F1 para reintentar la extracción IA dentro del mismo lote cuando el
proveedor falla de forma transitoria (p. ej. cuota 429). El parámetro ``dormir``
se inyecta para poder testear sin esperas reales.
"""

from __future__ import annotations

import logging
import time
from typing import Any, Callable, TypeVar

LOG = logging.getLogger("agente_rrhh")

T = TypeVar("T")


def con_reintentos(
    fn: Callable[[], T],
    *,
    intentos: int = 2,
    espera_base: float = 1.5,
    dormir: Callable[[float], Any] = time.sleep,
    excepciones: tuple[type[BaseException], ...] = (Exception,),
    etiqueta: str = "",
) -> T:
    """Ejecuta ``fn()`` hasta ``intentos`` veces con backoff exponencial.

    Lanza la última excepción capturada si se agotan los intentos.
    """
    ultimo: BaseException | None = None
    for numero in range(1, max(1, intentos) + 1):
        try:
            return fn()
        except excepciones as exc:  # noqa: PERF203 - reintento explícito
            ultimo = exc
            if numero >= intentos:
                break
            espera = espera_base * (2 ** (numero - 1))
            sufijo = f" ({etiqueta})" if etiqueta else ""
            LOG.warning(
                "Reintento %d/%d%s tras fallo: %s", numero, intentos, sufijo, exc
            )
            if espera > 0:
                dormir(espera)
    assert ultimo is not None
    raise ultimo
