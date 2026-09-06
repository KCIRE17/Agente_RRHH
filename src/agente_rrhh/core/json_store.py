"""Persistencia de candidatos en archivos JSON (capa silver del medallion).

Reemplaza a MongoDB: misma interfaz que el antiguo MongoDatabase para que el
pipeline y las fases F2/F3 no cambien su lógica de negocio.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import tempfile
from pathlib import Path
from typing import Any

LOG = logging.getLogger("agente_rrhh")

ESTADO_REINTENTO = "Pendiente: Reintento IA"


def _hash_mensaje_id(mensaje_id: str) -> str:
    """Identifica un mensaje de forma segura para usarse como nombre de archivo."""
    return hashlib.sha1(mensaje_id.encode("utf-8")).hexdigest()


class JsonStore:
    """Guarda un documento JSON por candidato en silver/candidatos/<hash>.json."""

    def __init__(self, dir_base: str | Path, subcarpeta: str = "candidatos") -> None:
        self._dir = Path(dir_base) / subcarpeta
        self._dir.mkdir(parents=True, exist_ok=True)

    def _ruta(self, mensaje_id: str) -> Path:
        return self._dir / f"{_hash_mensaje_id(mensaje_id)}.json"

    # ------------------------------------------------ mismas firma y semántica
    def _crear_indice_idempotente(self) -> None:
        self._dir.mkdir(parents=True, exist_ok=True)

    def verificar_conexion(self) -> None:
        if not self._dir.is_dir():
            raise RuntimeError(f"No se pudo acceder al store JSON: {self._dir}")

    def existe_mensaje(self, mensaje_id: str) -> bool:
        return self._ruta(mensaje_id).exists()

    def guardar_candidato(self, documento: dict[str, Any]) -> bool:
        """Guarda el JSON. Devuelve False si ya existía (idempotencia)."""
        ruta = self._ruta(documento.get("mensaje_id", ""))
        if ruta.exists():
            return False
        self._escribir(ruta, documento)
        return True

    def pendientes_reintento(self) -> list[dict[str, Any]]:
        pendientes = []
        for ruta in sorted(self._dir.glob("*.json")):
            documento = self._leer(ruta)
            if documento and documento.get("estado_procesamiento") == ESTADO_REINTENTO:
                pendientes.append(documento)
        return pendientes

    def actualizar_tras_reintento(self, mensaje_id: str, campos: dict[str, Any]) -> None:
        ruta = self._ruta(mensaje_id)
        documento = self._leer(ruta)
        if documento is None:
            LOG.warning("Reintento: no existe el JSON para %s", mensaje_id)
            return
        documento.update(campos)
        self._escribir(ruta, documento)

    def candidatos(self, estado: str | None = None) -> list[dict[str, Any]]:
        """Lista todos los candidatos, opcionalmente filtrados por estado."""
        docs: list[dict[str, Any]] = []
        for ruta in sorted(self._dir.glob("*.json")):
            doc = self._leer(ruta)
            if doc is None:
                continue
            if estado is None or doc.get("estado_procesamiento") == estado:
                docs.append(doc)
        return docs

    def cerrar(self) -> None:
        pass

    # ------------------------------------------------------------ bajo nivel
    def _leer(self, ruta: Path) -> dict[str, Any] | None:
        try:
            with ruta.open("r", encoding="utf-8") as f:
                return json.load(f)
        except (OSError, json.JSONDecodeError) as exc:
            LOG.warning("No se pudo leer %s: %s", ruta, exc)
            return None

    def _escribir(self, ruta: Path, documento: dict[str, Any]) -> None:
        ruta.parent.mkdir(parents=True, exist_ok=True)
        fd, temporal = tempfile.mkstemp(
            dir=str(ruta.parent), suffix=".tmp", prefix=".escribiendo-"
        )
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(documento, f, ensure_ascii=False, indent=2)
            os.replace(temporal, ruta)
        finally:
            if os.path.exists(temporal):
                os.unlink(temporal)