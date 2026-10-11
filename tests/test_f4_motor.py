"""F4 - Motor del chatbot: clasificacion de intenciones (offline, $0)."""

from __future__ import annotations

import pytest

from src.agente_rrhh.chatbot.motor import MotorChat, normalizar
from src.agente_rrhh.chatbot.preguntas_generales import buscar, todas
from src.agente_rrhh.chatbot.sesion import Sesion


@pytest.fixture
def motor(cfg_demo):
    return MotorChat(cfg_demo)


def _intencion(motor, mensaje, sesion=None):
    return motor.resolver(mensaje, sesion or Sesion("test"))["intencion"]


@pytest.mark.parametrize(
    "mensaje,esperado",
    [
        ("hola", "saludo"),
        ("que puedes hacer", "ayuda"),
        ("", "ayuda"),
        ("nuevo chat", "reiniciar"),
        ("cuanto hemos gastado en IA", "costos"),
        ("compara a Ana con Carla", "comparar"),
        ("cual es el origen de las postulaciones", "origen"),
        ("quienes pasan a fase tecnica", "fase_tecnica"),
        ("escribe un correo de rechazo", "borrador"),
        ("cuales son las brechas mas comunes", "brechas"),
        ("ranking de ANALISTA DE DATOS", "ranking"),
        ("cuantas postulaciones hay", "pipeline"),
        ("qwerty zxcvb", "fallback"),
    ],
)
def test_clasificacion_de_intenciones(motor, mensaje, esperado):
    assert _intencion(motor, mensaje) == esperado


def test_respuesta_offline_no_usa_ia(motor):
    respuesta = motor.resolver("hola", Sesion("s"))
    assert respuesta["modo"] == "offline"
    assert respuesta["uso"] is None


def test_normalizar():
    assert normalizar("  Café  ") == "CAFE"
    assert normalizar(None) == ""


def test_seguimiento_recuerda_candidato(motor):
    sesion = Sesion("s")
    _, filas = __import__(
        "src.agente_rrhh.chatbot.datos", fromlist=["datos"]
    ).ranking(motor._cfg, "ANALISTA_DE_DATOS")
    nombre = filas[0]["nombre"]
    motor.resolver(f"quien es {nombre}", sesion)
    assert sesion.candidato_nombre
    assert _intencion(motor, "y su telefono", sesion) == "candidato"


def test_buscar_preguntas_generales():
    faq = buscar("como se calcula el score")
    assert faq is not None
    assert "50%" in faq["respuesta"]
    assert len(todas()) == 8
