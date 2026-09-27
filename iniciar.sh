#!/usr/bin/env bash
# ===================================================================
#  Agente RRHH - arranque de un clic para entrega en otra laptop
#  (macOS / Linux). Equivalente de INICIAR.bat: prepara el entorno,
#  siembra los datos ficticios y abre el chatbot (F4) y el dashboard (F3).
#
#  Uso:  ./iniciar.sh
# ===================================================================
set -u
cd "$(dirname "$0")"

VPY=".venv/bin/python"
REQS="requirements-full.txt"
STAMP=".venv/.deps_ok"

echo
echo " =========================================================="
echo "   AGENTE RRHH  -  entrega de un clic  (F1 F2 F3 F4)"
echo " =========================================================="
echo

# ---------- 1) Python 3.12 o superior ----------
detect_python() {
  for candidato in python3.12 python3 python; do
    if command -v "$candidato" >/dev/null 2>&1 &&
       "$candidato" -c 'import sys; sys.exit(0 if sys.version_info>=(3,12) else 1)' 2>/dev/null; then
      LAUNCHER="$candidato"
      return 0
    fi
  done
  return 1
}

if ! detect_python; then
  echo " [1/4] No se encontro Python 3.12 o superior en esta laptop."
  echo "       Instálalo con:  brew install python@3.12   (macOS)"
  echo "       o descárgalo de https://www.python.org/downloads/"
  exit 1
fi
echo " [1/4] Python listo: $LAUNCHER"

# ---------- 2) Entorno virtual ----------
# Se valida que el .venv funcione de verdad: si la carpeta se copió a otra
# laptop, sus rutas absolutas quedan obsoletas y hay que rehacerlo.
if [ -x "$VPY" ] && "$VPY" -c "import fastapi, streamlit, docx, pdfplumber" 2>/dev/null; then
  echo " [2/4] Entorno virtual listo."
else
  if [ -d ".venv" ]; then
    echo " [2/4] El entorno virtual no es válido en este equipo; se rehace."
    rm -rf .venv
  fi
  echo " [2/4] Creando el entorno virtual .venv (solo la primera vez)..."
  "$LAUNCHER" -m venv .venv || { echo "No se pudo crear el entorno virtual."; exit 1; }
  echo " [2/4] Entorno virtual listo."
fi

# ---------- 3) Dependencias ----------
if ! "$VPY" -c "
import pathlib, sys
r = pathlib.Path('$REQS'); s = pathlib.Path('$STAMP')
sys.exit(0 if s.exists() and s.stat().st_mtime >= r.stat().st_mtime else 1)
" 2>/dev/null; then
  echo " [3/4] Instalando dependencias (solo la primera vez, 1-3 min)..."
  "$VPY" -m pip install --disable-pip-version-check --quiet --upgrade pip
  "$VPY" -m pip install --disable-pip-version-check --quiet -r "$REQS" || {
    echo "No se pudieron instalar las dependencias (revisa la conexion a internet)."
    exit 1
  }
  "$VPY" -c "import pathlib; pathlib.Path('$STAMP').touch()"
fi
echo " [3/4] Dependencias listas."

# ---------- 4) Sistema ----------
echo " [4/4] Iniciando el sistema..."
echo
exec "$VPY" main.py demo "$@"
