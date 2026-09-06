"""Extracción de texto plano desde PDF, DOCX, TXT y MD (o cuerpo del correo)."""

from __future__ import annotations

import io
import os

import docx
import pdfplumber

from ..core.config import EXTENSIONES_PERMITIDAS


class ErrorExtraccion(Exception):
    """Base de errores de extracción."""


class ArchivoIlegibleError(ErrorExtraccion):
    """PDF escaneado/corrupto o documento que no permite leer su texto."""


class FormatoNoPermitidoError(ErrorExtraccion):
    """Extensión del adjunto fuera de la lista permitida."""


def _extraer_pdf(datos: bytes) -> str:
    try:
        with pdfplumber.open(io.BytesIO(datos)) as pdf:
            paginas = [pagina.extract_text() for pagina in pdf.pages]
    except Exception as exc:  # PDF dañado o sin capa de texto
        raise ArchivoIlegibleError(f"No se pudo abrir el PDF: {exc}") from exc

    texto = "\n".join(t for t in paginas if t)
    if not texto.strip():
        raise ArchivoIlegibleError("PDF escaneado (imagen sin capa de texto) o vacío.")
    return texto


def _extraer_docx(datos: bytes) -> str:
    try:
        documento = docx.Document(io.BytesIO(datos))
    except Exception as exc:
        raise ArchivoIlegibleError(f"DOCX dañado o ilegible: {exc}") from exc

    parrafos = [p.text for p in documento.paragraphs]
    for tabla in documento.tables:
        for fila in tabla.rows:
            parrafos.append(" | ".join(celda.text for celda in fila.cells))
    texto = "\n".join(parrafos)
    if not texto.strip():
        raise ArchivoIlegibleError("DOCX sin contenido de texto.")
    return texto


def _extraer_txt(datos: bytes) -> str:
    for codificacion in ("utf-8", "latin-1"):
        try:
            return datos.decode(codificacion)
        except UnicodeDecodeError:
            continue
    return datos.decode("utf-8", errors="replace")


def formato_origen(nombre_archivo: str) -> str:
    return os.path.splitext(nombre_archivo)[1].lstrip(".").upper()


def extraer_adjunto(nombre_archivo: str, contenido: bytes) -> str:
    """Devuelve el texto plano de un adjunto según su extensión."""
    extension = os.path.splitext(nombre_archivo)[1].lower()
    if extension not in EXTENSIONES_PERMITIDAS:
        raise FormatoNoPermitidoError(f"Formato '{extension}' no permitido.")

    if extension == ".pdf":
        return _extraer_pdf(contenido)
    if extension == ".docx":
        return _extraer_docx(contenido)
    return _extraer_txt(contenido)