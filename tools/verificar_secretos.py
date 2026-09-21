#!/usr/bin/env python
"""Escáner anti-secretos (guard local). Detecta claves/tokens en el repo.

Pensado para correr antes de cada commit (ver ``.githooks/pre-commit``) y de
forma manual:

    uv run python tools/verificar_secretos.py            # archivos rastreados
    uv run python tools/verificar_secretos.py ARCHIVO... # archivos concretos

Sin argumentos escanea los archivos rastreados por git; con argumentos escanea
solo esos (el hook le pasa los archivos en stage). No imprime el secreto
completo (lo enmascara) y termina con código 1 si halla algo.
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

DIR_RAIZ = Path(__file__).resolve().parents[1]

# (etiqueta, patrón). Se exige una longitud mínima para no marcar placeholders.
PATRONES: list[tuple[str, re.Pattern[str]]] = [
    ("Google API key (AIza)", re.compile(r"AIza[0-9A-Za-z_\-]{35}")),
    # Formato nuevo de claves Google Cloud/Gemini (2025+): AQ.Ab<40+ chars>.
    ("Google API key (AQ.Ab)", re.compile(r"\bAQ\.Ab[0-9A-Za-z_\-]{40,}")),
    ("Groq API key", re.compile(r"gsk_[0-9A-Za-z]{20,}")),
    ("Token estilo OpenAI", re.compile(r"\bsk-[0-9A-Za-z]{20,}")),
    ("Token GitHub", re.compile(r"\bghp_[0-9A-Za-z]{20,}")),
    ("Bloque de clave privada", re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")),
]

# Valores que NO son secretos reales (plantillas de .env.example, etc.).
PLACEHOLDERS = re.compile(
    r"^(?:|tu[_-]?|your[_-]?|cambia|pon|xxx+|\.\.\.|<.*>|\[.*\]|"
    r"aqui|aqu[ií]|reemplaza|placeholder|example|dummy)",
    re.IGNORECASE,
)

MAX_BYTES = 2 * 1024 * 1024


def _enmascarar(valor: str) -> str:
    if len(valor) <= 8:
        return "*" * len(valor)
    return f"{valor[:4]}...{valor[-4:]}"


def _es_placeholder(valor: str) -> bool:
    coincidencia = PLACEHOLDERS.match(valor.strip())
    return bool(coincidencia and coincidencia.group()) or len(set(valor)) < 4


def _archivos_rastreados() -> list[Path]:
    try:
        salida = subprocess.run(
            ["git", "ls-files"],
            cwd=DIR_RAIZ,
            capture_output=True,
            text=True,
            check=True,
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        return [p for p in DIR_RAIZ.rglob("*") if p.is_file()]
    return [DIR_RAIZ / linea for linea in salida.stdout.splitlines() if linea]


def _revisar(ruta: Path) -> list[tuple[int, str, str, str]]:
    """Devuelve hallazgos (linea, etiqueta, patron, recorte) de un archivo."""
    try:
        if ruta.stat().st_size > MAX_BYTES:
            return []
        texto = ruta.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return []

    hallazgos: list[tuple[int, str, str, str]] = []
    for numero, linea in enumerate(texto.splitlines(), start=1):
        for etiqueta, patron in PATRONES:
            for coincidencia in patron.finditer(linea):
                if _es_placeholder(coincidencia.group()):
                    continue
                hallazgos.append(
                    (numero, etiqueta, coincidencia.group(), _enmascarar(coincidencia.group()))
                )
    return hallazgos


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Escáner anti-secretos del repo.")
    parser.add_argument("archivos", nargs="*", help="Rutas a escanear (por defecto, las rastreadas).")
    args = parser.parse_args(argv)

    if args.archivos:
        if args.archivos == ["-"]:
            candidatos = [Path(a) for a in sys.stdin.read().splitlines() if a]
        else:
            candidatos = [Path(a) for a in args.archivos]
    else:
        candidatos = _archivos_rastreados()

    total = 0
    for ruta in candidatos:
        if not ruta.is_absolute():
            ruta = (DIR_RAIZ / ruta).resolve()
        if not ruta.is_file():
            continue
        for numero, etiqueta, patron, recorte in _revisar(ruta):
            rel = ruta.relative_to(DIR_RAIZ) if ruta.is_absolute() else ruta
            print(f"{rel}:{numero}: {etiqueta} detectada -> {recorte} (patron {patron[:12]}...)")
            total += 1

    if total:
        print(f"\n[FALLO] {total} posible(s) secreto(s) detectado(s). No se debe commitear.")
        return 1
    print("[OK] Sin secretos detectados.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
