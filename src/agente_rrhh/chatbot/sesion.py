"""Contexto ligero de conversacion por sesion (en memoria).

No guarda historial completo: solo recuerda la *entidad en foco* (vacante y
candidato) para responder seguimientos como "¿y su telefono?". Se resetea con
"Nuevo chat". Ademas lleva el contador de consultas IA del modo demo (3 por
conversacion).
"""

from __future__ import annotations

import threading
import uuid
from typing import Any


class Sesion:
    """Estado minimo de una conversacion de chat."""

    def __init__(self, sesion_id: str, limite_ia: int | None = None) -> None:
        self.sesion_id = sesion_id
        self.vacante_carpeta: str | None = None
        self.candidato_id: str | None = None
        self.candidato_nombre: str | None = None
        # None = sin limite de IA; >0 = consultas restantes del modo demo.
        self.ia_restantes: int | None = limite_ia

    def limite(self, vacante_carpeta: str | None) -> None:
        self.vacante_carpeta = vacante_carpeta

    def en_foco_candidato(self, candidato_id: str, nombre: str) -> None:
        self.candidato_id = candidato_id
        self.candidato_nombre = nombre

    def reiniciar(self, limite_ia: int | None = None) -> None:
        self.vacante_carpeta = None
        self.candidato_id = None
        self.candidato_nombre = None
        # El limite del modo demo se restablece con "Nuevo chat".
        if limite_ia is not None:
            self.ia_restantes = limite_ia

    def usar_ia(self) -> bool:
        """Consume una consulta IA; False cuando se agotó el límite demo."""
        if self.ia_restantes is None:
            return True
        if self.ia_restantes <= 0:
            return False
        self.ia_restantes -= 1
        return True

    def resumen(self) -> dict[str, Any]:
        return {
            "vacante_carpeta": self.vacante_carpeta,
            "vacante_id": (
                self.vacante_carpeta.replace("_", " ") if self.vacante_carpeta else None
            ),
            "candidato_id": self.candidato_id,
            "candidato_nombre": self.candidato_nombre,
            "ia_restantes": self.ia_restantes,
        }


class AlmacenSesiones:
    """Registro de sesiones (identificadas por UUID) con lock."""

    def __init__(self, limite_ia: int | None = None) -> None:
        self._sesiones: dict[str, Sesion] = {}
        self._lock = threading.Lock()
        self._limite_ia = limite_ia

    def nueva(self) -> str:
        sesion_id = uuid.uuid4().hex
        with self._lock:
            self._sesiones[sesion_id] = Sesion(sesion_id, self._limite_ia)
        return sesion_id

    def obtener(self, sesion_id: str) -> Sesion:
        with self._lock:
            sesion = self._sesiones.get(sesion_id)
        if sesion is None:
            sesion = Sesion(sesion_id, self._limite_ia)
            with self._lock:
                self._sesiones[sesion_id] = sesion
        return sesion