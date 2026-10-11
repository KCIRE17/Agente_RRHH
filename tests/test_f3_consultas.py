"""F3 - Capa de consultas del dashboard (sin Streamlit)."""

from __future__ import annotations

from src.agente_rrhh.dashboard import consultas

GOLD = "data_demo/gold"
SILVER = "data_demo/silver"


def test_listar_vacantes_con_ranking():
    vacantes = consultas.listar_vacantes_con_ranking(GOLD)
    assert len(vacantes) == 3
    for v in vacantes:
        assert v["total"] == 10
        assert v["carpeta"] == v["carpeta"].upper()
        assert v["vacante_id"]


def test_ranking_ordenado_y_con_posiciones():
    vacante_id, filas = consultas.ranking_vacante(GOLD, "ANALISTA_DE_DATOS")
    assert vacante_id == "ANALISTA DE DATOS"
    assert len(filas) == 10
    scores = [f["match_score"] for f in filas]
    assert scores == sorted(scores, reverse=True)
    assert [f["posicion"] for f in filas] == list(range(1, 11))


def test_detalle_candidato_une_silver_y_desglose():
    _, filas = consultas.ranking_vacante(GOLD, "ANALISTA_DE_DATOS")
    top = filas[0]
    doc = consultas.detalle_candidato(
        GOLD, SILVER, "ANALISTA_DE_DATOS", top["id_candidato"]
    )
    assert doc is not None
    assert doc["id_candidato"] == top["id_candidato"]
    assert doc["silver"] is not None
    assert set(doc["puntos_por_bloque"]) == {"Habilidades", "Experiencia", "Formación"}


def test_detalle_candidato_inexistente():
    assert (
        consultas.detalle_candidato(GOLD, SILVER, "ANALISTA_DE_DATOS", "no-existe")
        is None
    )


def test_resumen_ingesta_por_estado_y_vacante():
    resumen = consultas.resumen_ingesta(SILVER, GOLD)
    assert resumen["total_silver"] == 33
    assert sum(resumen["por_estado"].values()) == 33
    fila = resumen["por_vacante"]["ANALISTA DE DATOS"]
    assert fila["total"] == 11
    assert fila["evaluados"] == 10


def test_sugerencia_clasificacion():
    assert consultas.sugerencia_clasificacion("Alta")["titulo"] == "Pase a fase técnica"
    assert consultas.sugerencia_clasificacion("Media")["titulo"] == "Revisión manual"
    assert consultas.sugerencia_clasificacion("Baja")["titulo"] == "No avanza"
    assert consultas.sugerencia_clasificacion("desconocido")["titulo"] == "No avanza"


def test_estado_amigable():
    assert consultas.estado_amigable("Listo para Evaluación") == "Pendiente de evaluación"
    assert consultas.estado_amigable("Evaluado") == "Evaluado"
    assert consultas.estado_amigable("") == "Sin información"
