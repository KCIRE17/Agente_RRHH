"""Punto de entrada ASGI para Vercel (deploy MVP del chatbot F4).

Vercel espera un objeto `app` importable a nivel de módulo en ``api/``.
Este archivo:
  - agrega la raíz del repo a ``sys.path`` (el paquete vive en ``src/``);
  - usa ``DATA_DIR=data_demo`` por defecto (datos ficticios versionados);
  - deja que ``PROVEEDOR_CHAT`` y ``GROQ_API_KEY`` lleguen vía Env Vars.

Local (con `main.py chat`) este archivo NO se usa; sigue valiendo uvicorn.
"""

import os
import sys
from pathlib import Path

_RAIZ = Path(__file__).resolve().parents[1]
if str(_RAIZ) not in sys.path:
    sys.path.insert(0, str(_RAIZ))

# Los datos demo viven en el repo (git) y son 100 % ficticios.
os.environ.setdefault("DATA_DIR", "data_demo")

from src.agente_rrhh.chatbot.api import crear_app

app = crear_app()