"""Contexto ligero de conversacion por sesion.

Recuerda la *entidad en foco* (vacante y candidato) para responder seguimientos
como "¿y su telefono?", guarda un historial corto de mensajes y, opcionalmente,
persiste la sesion a disco (``CHAT_PERSISTENCIA=1``). Se resetea con "Nuevo
chat". Ademas lleva el contador de consultas IA del modo demo (3 por
conversacion).
"""

from __future__ import annotations

import json
import logging
import threading
import uuid
from pathlib import Path
from typing import Any

LOG = logging.getLogger("agente_rrhh")

# Máximo de mensajes guardados en el historial de una sesión.
_MAX_HISTORIAL = 50


class Sesion:
    """Estado minimo de una conversacion de chat."""

    def __init__(self, sesion_id: str, limite_ia: int | None = None) -> None:
        self.sesion_id = sesion_id
        self.vacante_carpeta: str | None = None
        self.candidato_id: str | None = None
        self.candidato_nombre: str | None = None
        # None = sin limite de IA; >0 = consultas restantes del modo demo.
        self.ia_restantes: int | None = limite_ia
        self.historial: list[dict[str, Any]] = []

    def limite(self, vacante_carpeta: str | None) -> None:
        self.vacante_carpeta = vacante_carpeta

    def en_foco_candidato(self, candidato_id: str, nombre: str) -> None:
        self.candidato_id = candidato_id
        self.candidato_nombre = nombre

    def agregar_historial(self, rol: str, texto: str, **extra: Any) -> None:
        """Añade un turno al historial (recorta al máximo configurado)."""
        entrada = {"rol": rol, "texto": texto}
        entrada.update(extra)
        self.historial.append(entrada)
        if len(self.historial) > _MAX_HISTORIAL:
            self.historial = self.historial[-_MAX_HISTORIAL:]

    def reiniciar(self, limite_ia: int | None = None) -> None:
        self.vacante_carpeta = None
        self.candidato_id = None
        self.candidato_nombre = None
        self.historial = []
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

    def to_dict(self) -> dict[str, Any]:
        return {
            "sesion_id": self.sesion_id,
            "vacante_carpeta": self.vacante_carpeta,
            "candidato_id": self.candidato_id,
            "candidato_nombre": self.candidato_nombre,
            "ia_restantes": self.ia_restantes,
            "historial": self.historial,
        }

    @classmethod
    def from_dict(cls, datos: dict[str, Any]) -> "Sesion":
        sesion = cls(
            str(datos.get("sesion_id") or uuid.uuid4().hex),
            datos.get("ia_restantes"),
        )
        sesion.vacante_carpeta = datos.get("vacante_carpeta")
        sesion.candidato_id = datos.get("candidato_id")
        sesion.candidato_nombre = datos.get("candidato_nombre")
        sesion.historial = list(datos.get("historial") or [])
        return sesion


class AlmacenSesiones:
    """Registro de sesiones (identificadas por UUID) con lock.

    Si ``dir_persistencia`` es una ruta, cada sesion se serializa a
    ``<dir_persistencia>/<sesion_id>.json`` (historial incluido) y se recupera al
    volver a pedirla. Por defecto es ``None`` (100% en memoria).
    """

    def __init__(
        self,
        limite_ia: int | None = None,
        dir_persistencia: str | Path | None = None,
    ) -> None:
        self._sesiones: dict[str, Sesion] = {}
        self._lock = threading.Lock()
        self._limite_ia = limite_ia
        self._dir = Path(dir_persistencia) if dir_persistencia else None
        if self._dir is not None:
            self._dir.mkdir(parents=True, exist_ok=True)

    @property
    def persistencia(self) -> bool:
        return self._dir is not None

    def _ruta(self, sesion_id: str) -> Path | None:
        if self._dir is None:
            return None
        return self._dir / f"{sesion_id}.json"

    def nueva(self) -> str:
        sesion_id = uuid.uuid4().hex
        with self._lock:
            self._sesiones[sesion_id] = Sesion(sesion_id, self._limite_ia)
        return sesion_id

    def obtener(self, sesion_id: str) -> Sesion:
        with self._lock:
            sesion = self._sesiones.get(sesion_id)
        if sesion is None:
            sesion = self._cargar(sesion_id) or Sesion(sesion_id, self._limite_ia)
            with self._lock:
                self._sesiones[sesion_id] = sesion
        return sesion

    def historial(self, sesion_id: str) -> list[dict[str, Any]]:
        return list(self.obtener(sesion_id).historial)

    def guardar(self, sesion: Sesion) -> None:
        """Persiste la sesión (no-op si la persistencia está desactivada)."""
        ruta = self._ruta(sesion.sesion_id)
        if ruta is None:
            return
        try:
            ruta.write_text(
                json.dumps(sesion.to_dict(), ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        except OSError as exc:
            LOG.warning("No se pudo persistir la sesion %s: %s", sesion.sesion_id, exc)

    def _cargar(self, sesion_id: str) -> Sesion | None:
        ruta = self._ruta(sesion_id)
        if ruta is None or not ruta.is_file():
            return None
        try:
            datos = json.loads(ruta.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            LOG.warning("No se pudo leer la sesion %s: %s", sesion_id, exc)
            return None
        return Sesion.from_dict(datos)
