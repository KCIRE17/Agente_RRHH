"""F1 - Persistencia: idempotencia y ranking en las capas silver y gold."""

from __future__ import annotations

import json

from src.agente_rrhh.core.gold_store import GoldStore
from src.agente_rrhh.core.json_store import JsonStore, _hash_mensaje_id


def test_hash_mensaje_id_es_sha1_hex():
    h = _hash_mensaje_id("mensaje-123")
    assert len(h) == 40
    assert all(c in "0123456789abcdef" for c in h)


def test_guardar_candidato_es_idempotente(tmp_path):
    store = JsonStore(tmp_path / "silver")
    doc = {"mensaje_id": "m1", "estado_procesamiento": "Listo para Evaluación"}
    assert store.guardar_candidato(doc) is True
    assert store.guardar_candidato(doc) is False
    assert store.existe_mensaje("m1") is True


def test_candidatos_filtra_por_estado(tmp_path):
    store = JsonStore(tmp_path / "silver")
    store.guardar_candidato(
        {"mensaje_id": "a", "estado_procesamiento": "Listo para Evaluación"}
    )
    store.guardar_candidato(
        {"mensaje_id": "b", "estado_procesamiento": "Error: Archivo Ilegible"}
    )
    assert len(store.candidatos()) == 2
    listos = store.candidatos(estado="Listo para Evaluación")
    assert len(listos) == 1
    assert listos[0]["mensaje_id"] == "a"


def test_flujo_de_reintento(tmp_path):
    store = JsonStore(tmp_path / "silver")
    store.guardar_candidato(
        {"mensaje_id": "r", "estado_procesamiento": "Pendiente: Reintento IA"}
    )
    assert len(store.pendientes_reintento()) == 1
    store.actualizar_tras_reintento(
        "r", {"estado_procesamiento": "Listo para Evaluación"}
    )
    assert store.pendientes_reintento() == []
    assert store.candidatos()[0]["estado_procesamiento"] == "Listo para Evaluación"


def test_escritura_atomica_no_deja_temporales(tmp_path):
    store = JsonStore(tmp_path / "silver")
    store.guardar_candidato({"mensaje_id": "x"})
    assert list((tmp_path / "silver" / "candidatos").glob("*.tmp")) == []


def test_gold_guarda_y_recalcula_ranking(tmp_path):
    store = GoldStore(tmp_path / "gold")
    store.guardar_evaluacion(
        "ANALISTA DE DATOS",
        {
            "id_candidato": "c1",
            "vacante_id": "ANALISTA DE DATOS",
            "nombre_completo": "Uno",
            "match_score": 60,
            "clasificacion": "Media",
        },
    )
    store.guardar_evaluacion(
        "ANALISTA DE DATOS",
        {
            "id_candidato": "c2",
            "vacante_id": "ANALISTA DE DATOS",
            "nombre_completo": "Dos",
            "match_score": 90,
            "clasificacion": "Alta",
        },
    )
    assert store.existe_evaluacion("ANALISTA DE DATOS", "c1")

    ruta = tmp_path / "gold" / "evaluacion" / "ANALISTA_DE_DATOS" / "ranking.json"
    ranking = json.loads(ruta.read_text(encoding="utf-8"))
    assert ranking["total"] == 2
    assert [f["id_candidato"] for f in ranking["candidatos"]] == ["c2", "c1"]
