"""Almacenamiento de los archivos originales de los postulantes (capa bronze)."""

from __future__ import annotations

import re
import uuid
from datetime import date
from pathlib import Path

_NOMBRE_SEGURO = re.compile(r"[^A-Za-z0-9 _.\-]")
_ESPACIOS = re.compile(r"[ _]+")
_COPIA_UUID = re.compile(r"^(.*?)_[0-9a-f]{8}(\.[^.]+)$")


def nombre_seguro(nombre: str) -> str:
    """Convierte un nombre en un componente de ruta seguro para Windows."""
    nombre = _ESPACIOS.sub("_", _NOMBRE_SEGURO.sub("_", nombre))
    return nombre.strip("._") or "archivo"


class RawStore:
    """Guarda en bronze/<fecha>/<vacante>/<archivo> y devuelve la ruta."""

    def __init__(self, base_dir: str = "data/bronze") -> None:
        self._base = Path(base_dir)

    def guardar(
        self,
        nombre: str,
        contenido: bytes,
        fecha: date,
        vacante: str,
    ) -> str | None:
        """Copia el archivo original. Devuelve la ruta relativa o None si está vacío."""
        if not contenido:
            return None

        carpeta = self._base / fecha.isoformat() / nombre_seguro(vacante)
        carpeta.mkdir(parents=True, exist_ok=True)

        destino = carpeta / nombre_seguro(nombre)
        if destino.exists():
            if destino.read_bytes() == contenido:
                return destino.as_posix()
            destino = carpeta / f"{destino.stem}_{uuid.uuid4().hex[:8]}{destino.suffix}"

        destino.write_bytes(contenido)
        return destino.as_posix()

    def deduplicar(self) -> list[Path]:
        """Elimina copias `_<uuid>` idénticas a su original. Devuelve lo borrado."""
        borrados: list[Path] = []
        for copia in self._base.rglob("*"):
            if not copia.is_file():
                continue
            coincide = _COPIA_UUID.match(copia.name)
            if not coincide:
                continue
            original = copia.with_name(f"{coincide.group(1)}{coincide.group(2)}")
            if original.is_file() and original.read_bytes() == copia.read_bytes():
                copia.unlink()
                borrados.append(copia)
        return borrados

    def limpiar_por_dias(self, dias: int) -> list[Path]:
        """Borra archivos de bronze con más de `dias` días de antigüedad."""
        if dias <= 0:
            return []
        limite = date.today().toordinal() - dias
        borrados: list[Path] = []
        for archivo in self._base.rglob("*"):
            if not archivo.is_file():
                continue
            mtime = date.fromtimestamp(archivo.stat().st_mtime)
            if mtime.toordinal() < limite:
                archivo.unlink()
                borrados.append(archivo)
        return borrados

    def limpiar_carpetas_vacias(self) -> None:
        """Borra carpetas vacías resultantes tras una limpieza."""
        for carpeta in sorted(
            (p for p in self._base.rglob("*") if p.is_dir()), reverse=True
        ):
            try:
                carpeta.rmdir()
            except OSError:
                pass