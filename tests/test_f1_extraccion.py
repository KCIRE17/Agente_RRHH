"""F1 - Ingesta: sanitizacion de texto y extraccion de adjuntos."""

from __future__ import annotations

import io

import docx
import pytest

from src.agente_rrhh.core.sanitizer import quitar_tildes, sanitizar
from src.agente_rrhh.ingestion.extractor import (
    ArchivoIlegibleError,
    FormatoNoPermitidoError,
    extraer_adjunto,
    formato_origen,
)


def test_quitar_tildes():
    assert quitar_tildes("ÁéÍóÚ Programación") == "AeIoU Programacion"
    assert quitar_tildes("Ñandú") == "Nandu"


def test_sanitizar_quita_control_y_colapsa_espacios():
    crudo = "café\t\tcon   espacios\x00\x07  y lineas\n\n\n\nfin  "
    assert sanitizar(crudo) == "cafe con espacios y lineas\n\nfin"


def test_sanitizar_normaliza_saltos_windows():
    assert sanitizar("a\r\nb\rc") == "a\nb\nc"


def test_sanitizar_vacios():
    assert sanitizar("") == ""
    assert sanitizar(None) == ""


def test_formato_origen():
    assert formato_origen("CV.PDF") == "PDF"
    assert formato_origen("hoja.docx") == "DOCX"
    assert formato_origen("sin_extension") == ""


def test_extraer_txt_utf8():
    assert extraer_adjunto("cv.txt", "Hola ñandú".encode("utf-8")) == "Hola ñandú"


def test_extraer_txt_fallback_latin1():
    texto = extraer_adjunto("cv.txt", "café".encode("latin-1"))
    assert "caf" in texto


def test_extraer_docx_valido():
    buf = io.BytesIO()
    documento = docx.Document()
    documento.add_paragraph("Experiencia con Python y SQL")
    documento.save(buf)
    texto = extraer_adjunto("cv.docx", buf.getvalue())
    assert "Python" in texto and "SQL" in texto


def test_formato_no_permitido():
    with pytest.raises(FormatoNoPermitidoError):
        extraer_adjunto("virus.exe", b"MZ\x00\x00")


def test_pdf_ilegible():
    with pytest.raises(ArchivoIlegibleError):
        extraer_adjunto("cv.pdf", b"esto no es un pdf real")


def test_docx_ilegible():
    with pytest.raises(ArchivoIlegibleError):
        extraer_adjunto("cv.docx", b"no soy un docx")
