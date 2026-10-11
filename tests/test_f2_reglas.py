"""F2 - Reglas de negocio: pesos 50/30/20, clamp 0-100 y umbrales."""

from __future__ import annotations

import pytest

from src.agente_rrhh.chatbot.simulador import normalizar_pesos
from src.agente_rrhh.core.vacantes import (
    ErrorRequisitos,
    RequisitosVacante,
    slug_vacante,
)
from src.agente_rrhh.evaluation.reglas import (
    PESOS,
    clasificar,
    componer_puntaje,
    normalizar_score,
)


def test_pesos_suman_uno():
    assert round(sum(PESOS.values()), 6) == 1.0


@pytest.mark.parametrize(
    "valor,esperado",
    [
        (None, 0),
        ("abc", 0),
        (-5, 0),
        (0, 0),
        (49.4, 49),
        (79.6, 80),
        (100, 100),
        (150, 100),
        (50, 50),
    ],
)
def test_normalizar_score_clampa(valor, esperado):
    assert normalizar_score(valor) == esperado


@pytest.mark.parametrize(
    "score,clase",
    [(100, "Alta"), (80, "Alta"), (79, "Media"), (50, "Media"), (49, "Baja"), (0, "Baja")],
)
def test_clasificar_umbrales(score, clase):
    assert clasificar(score) == clase


def test_componer_puntaje_con_desglose_completo():
    desglose, score = componer_puntaje(
        {"desglose": {"habilidades": 100, "experiencia": 100, "formacion": 100}}
    )
    assert score == 100
    assert desglose["habilidades"]["puntos"] == 50
    assert desglose["experiencia"]["puntos"] == 30
    assert desglose["formacion"]["puntos"] == 20


def test_componer_puntaje_mixto():
    _, score = componer_puntaje(
        {"desglose": {"habilidades": 90, "experiencia": 50, "formacion": 100}}
    )
    assert score == 45 + 15 + 20


def test_componer_puntaje_sin_desglose_usa_match_score():
    desglose, score = componer_puntaje({"match_score": 137})
    assert desglose == {}
    assert score == 100


def test_slug_vacante():
    assert slug_vacante("Analista de Datos") == "ANALISTA_DE_DATOS"
    assert slug_vacante("Ingeniería   en Sistemas") == "INGENIERIA_EN_SISTEMAS"
    assert slug_vacante("   ") == "SIN_VACANTE"


def test_requisitos_carga_vacante_demo():
    datos = RequisitosVacante("config/vacantes").cargar("ANALISTA DE DATOS")
    assert datos["vacante"] == "ANALISTA DE DATOS"
    assert "Python" in datos["requisitos"]["habilidades"]["esenciales"]


def test_requisitos_inexistente():
    with pytest.raises(ErrorRequisitos):
        RequisitosVacante("config/vacantes").cargar("VACANTE QUE NO EXISTE")


def test_normalizar_pesos_simulador():
    pesos = normalizar_pesos({"habilidades": 50, "experiencia": 30, "formacion": 20})
    assert pesos == {"habilidades": 0.5, "experiencia": 0.3, "formacion": 0.2}


def test_normalizar_pesos_en_cero_usa_default():
    assert normalizar_pesos({}) == {"habilidades": 0.5, "experiencia": 0.3, "formacion": 0.2}
