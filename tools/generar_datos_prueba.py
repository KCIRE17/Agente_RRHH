#!/usr/bin/env python
"""Generador de datos sinteticos de PRUEBA para el chatbot F4.

STANDALONE: no forma parte del proceso del proyecto (ni de main.py). Escribe
candidatos ficticios en ``data_pruebas/`` (separado de ``data/``, gitignored)
para validar la app sin tocar datos reales.

Uso:
    uv run python tools/generar_datos_prueba.py
    uv run python main.py chat   # con DATA_DIR=data_pruebas para probar
"""

from __future__ import annotations

import json
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.agente_rrhh.core.gold_store import GoldStore
from src.agente_rrhh.core.json_store import JsonStore

DIR_PRUEBAS = Path(__file__).resolve().parents[1] / "data_pruebas"
SILVER = JsonStore(DIR_PRUEBAS / "silver", subcarpeta="candidatos")
GOLD = GoldStore(DIR_PRUEBAS / "gold", subcarpeta="evaluacion")

SIN_SESGO = [
    "foto",
    "edad",
    "genero",
    "direccion",
    "estado_civil",
]


def _fecha() -> str:
    return datetime.now(timezone.utc).isoformat()


def _dominio(email: str) -> str:
    return email.split("@")[-1]


def _silver(
    vacante: str,
    id_cand: str,
    nombre: str,
    email: str,
    telefono: str,
    habilidades: list[str],
    puestos: list[dict],
    formaciones: list[dict],
    estado: str = "Listo para Evaluación",
) -> None:
    mensaje_id = f"<{id_cand}.prueba@correo.local>"
    documento = {
        "mensaje_id": mensaje_id,
        "id_candidato": id_cand,
        "vacante_id": vacante,
        "email_remitente": f"{nombre} <{email}>",
        "remitente_metadatos": {
            "nombre": nombre,
            "email": email,
            "dominio": _dominio(email),
        },
        "fecha_envio": "2026-09-04T10:00:00-05:00",
        "x_mailer": None,
        "ruta_archivo_raw": None,
        "formato_origen": "PDF",
        "datos_json": {
            "candidato": {"email_remitente": None, "formato_origen": "texto"},
            "datos_contacto": {
                "nombre_completo": nombre,
                "telefono": telefono,
                "email": email,
            },
            "datos_estructurados": {
                "habilidades": habilidades,
                "experiencia_laboral": puestos,
                "formacion_academica": formaciones,
                "certificaciones": [],
            },
            "control_sesgo": {"atributos_excluidos": SIN_SESGO},
        },
        "texto_crudo": None,
        "estado_procesamiento": estado,
        "motivo": None,
        "fecha_ingesta": _fecha(),
        "fecha_reintento": None,
    }
    SILVER.guardar_candidato(documento)


def _gold(
    vacante: str,
    id_cand: str,
    nombre: str,
    email: str,
    telefono: str,
    score: float,
    clase: str,
    desglose: dict,
    fortalezas: list[str],
    brechas: list[str],
    ausente: list[str],
    tokens: dict,
) -> None:
    documento = {
        "id_candidato": id_cand,
        "vacante_id": vacante,
        "mensaje_id": f"<{id_cand}.prueba@correo.local>",
        "nombre_completo": nombre,
        "telefono": telefono,
        "email_remitente": f"{nombre} <{email}>",
        "fecha_envio": "2026-09-04T10:00:00-05:00",
        "match_score": score,
        "clasificacion": clase,
        "desglose": desglose,
        "fortalezas": fortalezas,
        "brechas": brechas,
        "requisito_esencial_ausente": ausente,
        "justificacion": "Datos sinteticos de prueba para el chatbot F4.",
        "requisitos_evaluados": {
            "habilidades": {
                "esenciales": desglose.get("habilidades", {}).get("esenciales", []),
                "opcionales": desglose.get("habilidades", {}).get("opcionales", []),
            },
            "experiencia_minima_anos": desglose.get("experiencia_minima", 0),
            "formacion": {"carreras": desglose.get("formacion", {}).get("carreras", [])},
        },
        "proveedor": "groq",
        "modelo": "openai/gpt-oss-120b",
        "uso_tokens": tokens,
        "estado_procesamiento": "Evaluado",
        "fecha_evaluacion": _fecha(),
    }
    GOLD.guardar_evaluacion(vacante, documento)


def _des(habilidades: int, experiencia: int, formacion: int) -> dict:
    """Construye un desglose consistente con los pesos 50/30/20."""
    return {
        "habilidades": {"peso": 0.5, "parcial": habilidades, "puntos": round(habilidades * 0.5, 2)},
        "experiencia": {"peso": 0.3, "parcial": experiencia, "puntos": round(experiencia * 0.3, 2)},
        "formacion": {"peso": 0.2, "parcial": formacion, "puntos": round(formacion * 0.2, 2)},
    }


def generar() -> int:
    DIR_PRUEBAS.mkdir(parents=True, exist_ok=True)

    # --- ANALISTA DE DATOS -------------------------------------------------
    _silver(
        "ANALISTA DE DATOS", "a1b2c3d4e5f60718293a0b1c2d3e4f50",
        "ANA MARIA GOMEZ QUISPE", "ana.gomez@gmail.com", "51991234567",
        ["Python", "SQL Server", "Power BI", "Excel", "Pensamiento analítico",
         "Resolución de problemas", "Machine Learning", "Trabajo en equipo"],
        [{"puesto": "Analista de datos senior", "duracion_anos": 3,
          "descripcion": "Modelado, reportes en Power BI y automatizacion con Python."}],
        [{"grado": "Titulada", "carrera": "Ingeniería de Sistemas",
          "institucion": "UNI"}, {"grado": "Curso", "carrera": "Machine Learning",
          "institucion": "Coursera"}],
    )
    _gold(
        "ANALISTA DE DATOS", "a1b2c3d4e5f60718293a0b1c2d3e4f50",
        "ANA MARIA GOMEZ QUISPE", "ana.gomez@gmail.com", "51991234567",
        88.5, "Alta", _des(95, 90, 70),
        ["Domina Python, SQL Server, Power BI y Machine Learning",
         "3 anos de experiencia como analista de datos", "Titulo de Ingenieria de Sistemas"],
        ["No conoce Oracle a nivel avanzado"], [],
        {"prompt": 1400, "completado": 1200, "total": 2600},
    )

    _silver(
        "ANALISTA DE DATOS", "b2c3d4e5f60718293a0b1c2d3e4f5061",
        "LUIS ALBERTO TORRES RIOS", "luis.torres@hotmail.com", "51998765432",
        ["Python", "Excel", "Power BI", "Pensamiento analítico",
         "Trabajo en equipo", "SQL Server"],
        [{"puesto": "Practicante de datos", "duracion_anos": 1,
          "descripcion": "Limpieza de datos y tableros en Power BI."}],
        [{"grado": "Estudiante (7mo ciclo)", "carrera": "Ingeniería de Datos",
          "institucion": "UNMSM"}],
    )
    _gold(
        "ANALISTA DE DATOS", "b2c3d4e5f60718293a0b1c2d3e4f5061",
        "LUIS ALBERTO TORRES RIOS", "luis.torres@hotmail.com", "51998765432",
        64.5, "Media", _des(80, 45, 55),
        ["Solicito las habilidades esenciales de Python, SQL y Power BI",
         "Buena formacion en curso de Ingenieria de Datos"],
        ["Experiencia laboral limitada (solo practica de 1 ano)",
         "Aun no concluye su carrera"],
        [], {"prompt": 1380, "completado": 1210, "total": 2590},
    )

    _silver(
        "ANALISTA DE DATOS", "c3d4e5f60718293a0b1c2d3e4f506172",
        "LUCIA FERNANDA PAREDES", "lucia.paredes@outlook.com", "51995556677",
        ["Excel", "Office", "Trabajo en equipo", "Organizada"],
        [{"puesto": "Asistente administrativa", "duracion_anos": 2,
          "descripcion": "Tareas administrativas y reportes en Excel."}],
        [{"grado": "Bachiller", "carrera": "Administración", "institucion": "U. de Lima"}],
    )
    _gold(
        "ANALISTA DE DATOS", "c3d4e5f60718293a0b1c2d3e4f506172",
        "LUCIA FERNANDA PAREDES", "lucia.paredes@outlook.com", "51995556677",
        36.5, "Baja", _des(40, 35, 30),
        None,
        ["No domina Python, SQL Server ni Power BI", "Carrera no alineada con la vacante"],
        ["Python (esencial)", "SQL Server (esencial)", "Power BI (esencial)"],
        {"prompt": 1395, "completado": 1230, "total": 2625},
    )

    # --- CONTADOR ----------------------------------------------------------
    _silver(
        "CONTADOR", "d4e5f60718293a0b1c2d3e4f50617283",
        "PEDRO ANTONIO SALAS VEGA", "pedro.salas@gmail.com", "51993332211",
        ["Contabilidad general", "Tributación", "Excel avanzado", "SUNAT",
         "Conciliación bancaria", "Trabajo en equipo"],
        [{"puesto": "Contador", "duracion_anos": 5,
          "descripcion": "Cierres contables e impuestos."}],
        [{"grado": "Colegiado", "carrera": "Contabilidad", "institucion": "UNFV"}],
    )
    _gold(
        "CONTADOR", "d4e5f60718293a0b1c2d3e4f50617283",
        "PEDRO ANTONIO SALAS VEGA", "pedro.salas@gmail.com", "51993332211",
        90.5, "Alta", _des(90, 95, 85),
        None,
        ["5 anos como contador", "Colegiado", "Domina SUNAT y conciliaciones"],
        ["Sin experiencia internacional"],
        {"prompt": 1350, "completado": 1150, "total": 2500},
    )

    # --- Estados diversos (solo silver) ------------------------------------
    _silver(
        "ANALISTA DE DATOS", "e5f60718293a0b1c2d3e4f5061728394",
        "CARLOS NUNEZ ROJAS", "carlos.nunez@yahoo.com", "51997665431",
        ["Python", "Excel"],
        [], [],
        estado="Pendiente: Reintento IA",
    )
    _silver(
        "CONTADOR", "f60718293a0b1c2d3e4f5061728394a5",
        "KAREN RUIZ FLORES", "karen.ruiz@gmail.com", "51994445566",
        ["Excel"],
        [], [],
        estado="Error: Archivo Ilegible",
    )

    print(f"Datos de prueba generados en {DIR_PRUEBAS}")
    print("Para probar el chatbot con ellos:")
    print("  set DATA_DIR=data_pruebas && uv run python main.py chat --port 8510")
    return 0


if __name__ == "__main__":
    raise SystemExit(generar())