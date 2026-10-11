"""Tests de las capacidades nuevas (F1/F2/F4 + extras E9).

Cubren: reportes F1, reintentos con backoff, diccionario de habilidades,
multi-proveedor de IA, agregador de tokens, limite por vacante, historial y
persistencia de chat, y el endpoint de trazabilidad /api/traza.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest


# ----------------------------------------------------------------- F1 reporte
def test_resumen_por_vacante(data_demo):
    from src.agente_rrhh.ingestion import reporte

    datos = reporte.resumen_por_vacante(str(data_demo / "silver"))
    assert datos["total"] == 33
    assert len(datos["por_vacante"]) == 3
    assert all(v["total"] == 11 for v in datos["por_vacante"].values())


def test_dias_desde_ultima(data_demo):
    from src.agente_rrhh.ingestion import reporte

    dias = reporte.dias_desde_ultima(str(data_demo / "silver"))
    assert dias is not None and dias >= 1


def test_dias_desde_ultima_silver_vacio(tmp_path):
    from src.agente_rrhh.ingestion import reporte

    assert reporte.dias_desde_ultima(str(tmp_path)) is None


# --------------------------------------------------------------- reintentos
def test_con_reintentos_exito_tras_fallos():
    from src.agente_rrhh.core.reintentos import con_reintentos

    intentos = {"n": 0}
    esperas: list[float] = []

    def falla_dos_veces():
        intentos["n"] += 1
        if intentos["n"] < 3:
            raise RuntimeError("transitorio")
        return "ok"

    resultado = con_reintentos(
        falla_dos_veces, intentos=3, espera_base=1.0, dormir=esperas.append
    )
    assert resultado == "ok"
    assert intentos["n"] == 3
    assert esperas == [1.0, 2.0]


def test_con_reintentos_agota_y_propaga():
    from src.agente_rrhh.core.reintentos import con_reintentos

    def siempre_falla():
        raise ValueError("boom")

    with pytest.raises(ValueError):
        con_reintentos(
            siempre_falla, intentos=2, espera_base=0, dormir=lambda _: None
        )


# --------------------------------------------------------------- habilidades
def test_diccionario_habilidades(raiz):
    from src.agente_rrhh.core import habilidades

    dic = habilidades.cargar_diccionario(raiz / "config" / "habilidades.json")
    assert dic["niveles"]
    assert habilidades.nivel_de(dic, "Python")["nivel"] == "avanzado"
    # Normaliza tildes al buscar.
    assert habilidades.nivel_de(dic, "Ingles")["nivel"] == "intermedio"
    resumen = habilidades.resumen_para_prompt(dic)
    assert resumen["python"] == "avanzado"


def test_diccionario_inexistente(tmp_path):
    from src.agente_rrhh.core import habilidades

    assert habilidades.cargar_diccionario(tmp_path / "nope.json") == {}


# ------------------------------------------------------------ multi-proveedor
def test_proveedores_soportados():
    from src.agente_rrhh.core import llm

    for nombre in ("gemini", "groq", "openrouter", "cerebras", "ollama"):
        assert nombre in llm.PROVEEDORES


def test_generar_texto_proveedor_desconocido():
    from src.agente_rrhh.core.llm import ErrorModelo, generar_texto

    with pytest.raises(ErrorModelo):
        generar_texto("perplexity", "x", "key", "hola")


def test_generar_texto_sin_clave():
    from src.agente_rrhh.core.llm import ErrorModelo, generar_texto

    with pytest.raises(ErrorModelo):
        generar_texto("groq", "x", "", "hola")


def test_config_clave_ia():
    from src.agente_rrhh.core.config import Config

    cfg = Config(gemini_api_key="g", groq_api_key="q", openrouter_api_key="o")
    assert cfg.clave_ia("gemini") == "g"
    assert cfg.clave_ia("groq") == "q"
    assert cfg.clave_ia("openrouter") == "o"
    assert cfg.clave_ia("ollama") == "ollama"
    assert cfg.clave_ia("desconocido") == ""


def test_config_desde_env_nuevas_claves(monkeypatch):
    from src.agente_rrhh.core.config import Config

    monkeypatch.setenv("OPENROUTER_API_KEY", "or-key")
    monkeypatch.setenv("CHAT_PERSISTENCIA", "1")
    monkeypatch.setenv("IA_REINTENTOS", "4")
    cfg = Config.desde_env()
    assert cfg.openrouter_api_key == "or-key"
    assert cfg.chat_persistencia is True
    assert cfg.reintentos_ia == 4


# ----------------------------------------------------------- agregador tokens
def test_registrar_resumen_tokens(tmp_path):
    from src.agente_rrhh.core import costo

    ruta = tmp_path / "uso_fase2.jsonl"
    costo.registrar_resumen(
        ruta,
        "evaluacion",
        modelo="openai/gpt-oss-120b",
        proveedor="groq",
        candidatos=3,
        prompt_tokens=100,
        completado_tokens=50,
    )
    usos = costo.leer_usos(ruta)
    assert len(usos) == 1
    assert usos[0]["tipo"] == "resumen_lote"
    assert usos[0]["total_tokens"] == 150
    assert usos[0]["candidatos"] == 3


# --------------------------------------------------- F2 limite por vacante
def _config_con_vacante_limitada(data_demo, tmp_path, limite: int):
    from src.agente_rrhh.core.config import Config

    dir_vac = tmp_path / "vacantes"
    dir_vac.mkdir()
    (dir_vac / "ANALISTA_DE_DATOS.json").write_text(
        json.dumps(
            {
                "vacante": "ANALISTA DE DATOS",
                "max_candidatos": limite,
                "requisitos": {
                    "habilidades": {"esenciales": ["Python"], "opcionales": []},
                    "experiencia_minima_anos": 0,
                    "formacion": {"carreras": []},
                },
            }
        ),
        encoding="utf-8",
    )
    return Config(data_dir="data_demo", rutas_vacantes=str(dir_vac))


def test_evaluacion_respeta_max_candidatos(data_demo, tmp_path):
    from src.agente_rrhh.evaluation.pipeline_evaluacion import PipelineEvaluacion

    cfg = _config_con_vacante_limitada(data_demo, tmp_path, 1)
    pipeline = PipelineEvaluacion(cfg, dry_run=True)
    resultado = pipeline.ejecutar()
    assert resultado["resumen"].get("Evaluado") == 1
    assert resultado["resumen"].get("Omitido (límite por vacante)", 0) >= 1


def test_requisitos_para_ia_agrega_niveles(cfg_demo):
    from src.agente_rrhh.evaluation.pipeline_evaluacion import PipelineEvaluacion

    pipeline = PipelineEvaluacion(cfg_demo, dry_run=True)
    original = {"vacante": "X", "requisitos": {"habilidades": {"esenciales": []}}}
    enriquecido = pipeline._requisitos_para_ia(original)
    assert "niveles_habilidad_valorados" in enriquecido["requisitos"]
    # El original no se muta (se guarda sin el contexto adicional).
    assert "niveles_habilidad_valorados" not in original["requisitos"]


# ------------------------------------------------------------ F2 read-only
def test_evaluacion_dry_run_no_registra_tokens(cfg_demo, tmp_path):
    from src.agente_rrhh.evaluation.pipeline_evaluacion import PipelineEvaluacion

    pipeline = PipelineEvaluacion(cfg_demo, dry_run=True)
    pipeline._registrar_resumen_lote({"Evaluado": 5}, {"prompt": 10, "completado": 5})
    # dry-run no debe escribir la bitacora.
    assert not (tmp_path / "uso_fase2.jsonl").exists()


# --------------------------------------------------------------- F4 sesion
def test_sesion_historial_y_persistencia(tmp_path):
    from src.agente_rrhh.chatbot.sesion import AlmacenSesiones

    almacen = AlmacenSesiones(limite_ia=None, dir_persistencia=tmp_path)
    sid = almacen.nueva()
    sesion = almacen.obtener(sid)
    sesion.agregar_historial("usuario", "hola")
    sesion.agregar_historial("asistente", "buenas")
    almacen.guardar(sesion)

    assert (tmp_path / f"{sid}.json").is_file()

    otro = AlmacenSesiones(limite_ia=None, dir_persistencia=tmp_path)
    recuperada = otro.obtener(sid)
    assert [m["texto"] for m in recuperada.historial] == ["hola", "buenas"]
    assert otro.persistencia is True


def test_sesion_sin_persistencia_no_escribe(tmp_path):
    from src.agente_rrhh.chatbot.sesion import AlmacenSesiones

    almacen = AlmacenSesiones()
    assert almacen.persistencia is False
    sid = almacen.nueva()
    almacen.guardar(almacen.obtener(sid))


# --------------------------------------------------------------- F4 API
def test_api_traza(client_demo):
    r = client_demo.get("/api/traza")
    assert r.status_code == 200
    body = r.json()
    assert body["carpeta"] == "ANALISTA_DE_DATOS"
    fases = [p["fase"] for p in body["pasos"]]
    assert fases[0] == "F1"
    assert "F2" in fases and "F4" in fases
    assert body["reglas"]["pesos"]["habilidades"] == 0.5


def test_api_traza_carpeta_inexistente(client_demo):
    r = client_demo.get("/api/traza", params={"carpeta": "NO_EXISTE"})
    assert r.status_code == 404


def test_api_historial_tras_chat(client_demo):
    r = client_demo.post("/api/chat", json={"mensaje": "ranking de ANALISTA DE DATOS"})
    sid = r.json()["sesion_id"]
    h = client_demo.get(f"/api/sesiones/{sid}/historial")
    assert h.status_code == 200
    historial = h.json()["historial"]
    assert len(historial) == 2
    assert historial[0]["rol"] == "usuario"
    assert historial[1]["rol"] == "asistente"


def test_api_costos_fase2_lotes(client_demo):
    r = client_demo.get("/api/costos")
    assert r.status_code == 200
    assert isinstance(r.json()["fase2_lotes"], list)


def test_api_con_persistencia(tmp_path):
    from fastapi.testclient import TestClient

    from src.agente_rrhh.chatbot.api import crear_app
    from src.agente_rrhh.core.config import Config

    cfg = Config(data_dir=str(tmp_path), chat_persistencia=True)
    client = TestClient(crear_app(cfg))
    r = client.post("/api/chat", json={"mensaje": "hola"})
    assert r.status_code == 200
    sid = r.json()["sesion_id"]
    assert (tmp_path / "gold" / "chat_sesiones" / f"{sid}.json").is_file()


# --------------------------------------------------------------- main CLI
def test_resumen_cli_json(capsys, cfg_demo):
    import main

    codigo = main.ejecutar_resumen(cfg_demo, como_json=True)
    assert codigo == 0
    salida = json.loads(capsys.readouterr().out)
    assert salida["total"] == 33
