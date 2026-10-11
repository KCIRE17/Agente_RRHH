"""Configuracion compartida de pytest para el Agente RRHH.

- Fija el directorio de trabajo en la raiz del repo (para rutas relativas
  como config/, prompt/ y data_demo/).
- Expone fixtures reutilizables: un ``Config`` apuntando a los datos demo y
  clientes ``TestClient`` del chatbot F4 (login desactivado / habilitado).

Los tests trabajan contra ``data_demo`` (datos ficticios versionados) para ser
deterministas y no tocar datos reales de candidatos en ``data/``.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[1]
DATA_DEMO = RAIZ / "data_demo"

if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

os.chdir(RAIZ)


@pytest.fixture(scope="session")
def raiz() -> Path:
    return RAIZ


@pytest.fixture(scope="session")
def data_demo() -> Path:
    return DATA_DEMO


@pytest.fixture
def cfg_demo():
    from src.agente_rrhh.core.config import Config

    return Config(data_dir="data_demo")


@pytest.fixture
def client_demo(cfg_demo):
    from fastapi.testclient import TestClient

    from src.agente_rrhh.chatbot.api import crear_app

    return TestClient(crear_app(cfg_demo))


@pytest.fixture
def cfg_login():
    from src.agente_rrhh.core.config import Config

    return Config(
        data_dir="data_demo",
        admin_usuario="rrhh",
        admin_clave="clave-demo-123",
    )


@pytest.fixture
def client_login(cfg_login):
    from fastapi.testclient import TestClient

    from src.agente_rrhh.chatbot.api import crear_app

    return TestClient(crear_app(cfg_login))
