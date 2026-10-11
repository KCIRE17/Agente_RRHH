"""core.costo - calculo de costo, bitacora jsonl y resumen de tokens."""

from __future__ import annotations

import json

from src.agente_rrhh.core.costo import (
    calcular_costo,
    leer_tarifas,
    leer_usos,
    registrar_uso,
    resumir,
)


def test_calcular_costo_con_tarifa_del_modelo():
    costo = calcular_costo(1_000_000, 1_000_000, "openai/gpt-oss-120b")
    assert round(costo, 4) == 0.42


def test_calcular_costo_usa_defecto_para_modelo_desconocido():
    costo = calcular_costo(1_000_000, 0, "modelo-inexistente")
    assert round(costo, 4) == 0.1


def test_calcular_costo_modelo_gratuito():
    assert calcular_costo(1_000_000, 1_000_000, "gemini-3.5-flash") == 0.0


def test_leer_tarifas_tiene_defecto():
    tarifas = leer_tarifas("config/tarifas.json")
    assert "defecto" in tarifas


def test_bitacora_roundtrip(tmp_path):
    ruta = tmp_path / "uso_chat.jsonl"
    registro = registrar_uso(
        ruta,
        "chat",
        "gemini",
        "gemini-3.5-flash",
        100,
        50,
        ruta_tarifas="config/tarifas.json",
        pregunta="hola",
    )
    assert registro["total_tokens"] == 150
    assert registro["costo_usd"] == 0.0

    usos = leer_usos(ruta)
    assert len(usos) == 1
    assert usos[0]["pregunta"] == "hola"

    resumen = resumir(usos)
    assert resumen["llamadas"] == 1
    assert resumen["total_tokens"] == 150


def test_leer_usos_ignora_lineas_invalidas(tmp_path):
    ruta = tmp_path / "uso_chat.jsonl"
    ruta.write_text('{"total_tokens": 10}\nno-es-json\n', encoding="utf-8")
    usos = leer_usos(ruta)
    assert len(usos) == 1
    assert usos[0]["total_tokens"] == 10


def test_leer_usos_archivo_inexistente(tmp_path):
    assert leer_usos(tmp_path / "nada.jsonl") == []


def test_resumir_agrega_varios(tmp_path):
    usos = [{"total_tokens": 10, "costo_usd": 0.5}, {"total_tokens": 5, "costo_usd": 0.25}]
    resumen = resumir(usos)
    assert resumen == {"llamadas": 2, "total_tokens": 15, "costo_usd": 0.75}
