#!/usr/bin/env python
"""Generador de datos demo (30+ candidatos ficticios) para el deploy MVP Vercel.

STANDALONE: no forma parte del proceso del proyecto (ni de main.py). Escribe
``data_demo/`` (versionable en git) con el mismo esquema medallion de ``data/``
pero con candidatos 100 % ficticios y libres de datos personales reales.

Uso:
    uv run python tools/generar_datos_demo.py
    DATA_DIR=data_demo uv run python main.py chat --port 8510   # probar local
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.agente_rrhh.core.gold_store import GoldStore
from src.agente_rrhh.core.json_store import JsonStore
from src.agente_rrhh.core.vacantes import slug_vacante

DIR_DEMO = Path(__file__).resolve().parents[1] / "data_demo"
DIR_VACANTES = Path(__file__).resolve().parents[1] / "config" / "vacantes"

SILVER = JsonStore(DIR_DEMO / "silver", subcarpeta="candidatos")
GOLD = GoldStore(DIR_DEMO / "gold", subcarpeta="evaluacion")

SIN_SESGO = ["foto", "edad", "genero", "direccion", "estado_civil"]
NOMBRE_RANKING = "ranking.json"

PUESTOS_TITULOS = {
    "ANALISTA DE DATOS": {
        "puesto": "Analista de Datos",
        "junior": "Asistente de análisis de datos",
    },
    "EJECUTIVO COMERCIAL": {
        "puesto": "Ejecutivo de Ventas",
        "junior": "Asesor comercial",
    },
    "DESARROLLADOR BACKEND": {
        "puesto": "Desarrollador Backend",
        "junior": "Desarrollador Junior",
    },
}


def _fecha() -> str:
    return datetime.now(timezone.utc).isoformat()


def _dominio(email: str) -> str:
    return email.split("@")[-1]


def _leer_requisitos(vacante_id: str) -> dict:
    with (DIR_VACANTES / f"{slug_vacante(vacante_id)}.json").open(
        "r", encoding="utf-8"
    ) as f:
        return json.load(f)["requisitos"]


def _habilidades_parcial(n_esc: int, len_ess: int) -> int:
    return min(100, round(100 * n_esc / len_ess))


# ------------------------------------------------------------------- textos
def _textos(
    vacante_id: str, requisitos: dict, n_esc: int, hab: int,
    exp_p: int, form_p: int, exp_anos: float, score: int,
) -> tuple[list[str], list[str], list[str], str]:
    ess = requisitos["habilidades"]["esenciales"]
    ausentes = ess[n_esc:]

    fortalezas: list[str] = []
    if hab >= 85:
        fortalezas.append("Domina las habilidades esenciales para la vacante.")
    elif hab >= 55:
        fortalezas.append("Maneja la mayoría de las habilidades esenciales requeridas.")
    if exp_p >= 60:
        fortalezas.append(f"Aporta experiencia laboral alineada ({exp_anos:g} años).")
    if form_p >= 60:
        fortalezas.append("Formación académica acorde al perfil solicitado.")
    if not fortalezas:
        fortalezas.append("Cuenta con una base de habilidades aprovechable para la vacante.")

    brechas: list[str] = []
    for a in ausentes[:3]:
        brechas.append(f"No se evidencia dominio de {a}.")
    if exp_p < 50:
        brechas.append("Experiencia laboral todavía limitada para el nivel solicitado.")
    if form_p < 50:
        brechas.append("La formación académica no se alinea del todo con la vacante.")
    if not brechas:
        brechas.append("Sin brechas significativas detectadas en la evaluación.")

    justificacion = (
        f"Candidato evaluado para {vacante_id} con match score {score}/100 "
        f"usando los pesos 50/30/20 (habilidades, experiencia, formación)."
    )
    return fortalezas, brechas, ausentes, justificacion


# -------------------------------------------------------------------- silver
def _silver(
    vacante_id: str,
    id_cand: str,
    nombre: str,
    email: str,
    telefono: str,
    habilidades: list[str],
    puestos: list[dict],
    formaciones: list[dict],
    estado: str,
    motivo: str | None = None,
    texto_crudo: str | None = None,
    fecha_envio: str = "2026-09-06T09:00:00-05:00",
) -> None:
    documento = {
        "mensaje_id": f"<{id_cand}.demo@correo.local>",
        "id_candidato": id_cand,
        "vacante_id": vacante_id,
        "email_remitente": f"{nombre} <{email}>",
        "remitente_metadatos": {
            "nombre": nombre,
            "email": email,
            "dominio": _dominio(email),
        },
        "fecha_envio": fecha_envio,
        "x_mailer": None,
        "ruta_archivo_raw": None,
        "formato_origen": "PDF",
        "datos_json": (
            {
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
            }
            if estado == "Listo para Evaluación"
            else None
        ),
        "texto_crudo": texto_crudo,
        "estado_procesamiento": estado,
        "motivo": motivo,
        "fecha_ingesta": _fecha(),
        "fecha_reintento": None,
    }
    SILVER.guardar_candidato(documento)


# ---------------------------------------------------------------------- gold
def _gold(
    vacante_id: str,
    id_cand: str,
    nombre: str,
    email: str,
    telefono: str,
    fecha_envio: str,
    requisitos: dict,
    n_esc: int,
    desglose: dict,
    score: int,
    fortalezas: list[str],
    brechas: list[str],
    ausentes: list[str],
) -> None:
    documento = {
        "id_candidato": id_cand,
        "vacante_id": vacante_id,
        "mensaje_id": f"<{id_cand}.demo@correo.local>",
        "nombre_completo": nombre,
        "telefono": telefono,
        "email_remitente": f"{nombre} <{email}>",
        "fecha_envio": fecha_envio,
        "match_score": score,
        "clasificacion": _clasificar(score),
        "desglose": desglose,
        "fortalezas": fortalezas,
        "brechas": brechas,
        "requisito_esencial_ausente": ausentes,
        "justificacion": (
            f"Candidato evaluado para {vacante_id} con match score {score}/100 "
            f"usando los pesos 50/30/20 (habilidades, experiencia, formación)."
        ),
        "requisitos_evaluados": requisitos,
        "proveedor": "groq",
        "modelo": "openai/gpt-oss-120b",
        "uso_tokens": {
            "prompt": 1300 + score,
            "completado": 1100 + score // 2,
            "total": 2400 + score + score // 2,
        },
        "estado_procesamiento": "Evaluado",
        "fecha_evaluacion": _fecha(),
    }
    GOLD.guardar_evaluacion(vacante_id, documento)


def _clasificar(score: int) -> str:
    if score >= 80:
        return "Alta"
    if score >= 50:
        return "Media"
    return "Baja"


def _desglose(hab: int, exp: int, form: int) -> tuple[dict, int]:
    pesos = {"habilidades": 0.5, "experiencia": 0.3, "formacion": 0.2}
    desg = {
        k: {
            "peso": pesos[k],
            "parcial": v,
            "puntos": round(v * pesos[k]),
        }
        for k, v in {"habilidades": hab, "experiencia": exp, "formacion": form}.items()
    }
    return desg, sum(d["puntos"] for d in desg.values())


# ------------------------------------------------------------- definicion
def _candidato(
    vacante_id: str,
    requisitos: dict,
    nombre: str,
    email: str,
    telefono: str,
    n_esc: int,
    cnt_opt: int,
    exp_anos: float,
    exp_p: int,
    form_p: int,
    formaciones: list[dict],
    fecha_envio: str,
) -> None:
    ess = requisitos["habilidades"]["esenciales"]
    opt = requisitos["habilidades"]["opcionales"]
    habilidades = ess[:n_esc] + opt[:cnt_opt]
    hab = _habilidades_parcial(n_esc, len(ess))

    titulos = PUESTOS_TITULOS[vacante_id]
    puestos = [
        {
            "puesto": titulos["puesto"],
            "duracion_anos": exp_anos,
            "descripcion": (
                f"Funciones propias de {titulos['puesto'].lower()} en un equipo "
                "multidisciplinario, reportes y coordinación con stakeholders."
            ),
        }
    ]
    if exp_anos >= 4:
        puestos.insert(
            0,
            {
                "puesto": titulos["junior"],
                "duracion_anos": round(exp_anos - 2, 1),
                "descripcion": "Soporte y ejecución de tareas operativas del área.",
            },
        )

    id_cand = _id_para(vacante_id, nombre)

    _silver(
        vacante_id, id_cand, nombre, email, telefono, habilidades, puestos,
        formaciones, "Listo para Evaluación", fecha_envio=fecha_envio,
    )

    desg, score = _desglose(hab, exp_p, form_p)
    fortalezas, brechas, ausentes, justif = _textos(
        vacante_id, requisitos, n_esc, hab, exp_p, form_p, exp_anos, score
    )
    _gold(
        vacante_id, id_cand, nombre, email, telefono, fecha_envio, requisitos,
        n_esc, desg, score, fortalezas, brechas, ausentes,
    )
    return {"vacante_id": vacante_id, "nombre": nombre, "score": score}


def _id_para(vacante_id: str, nombre: str) -> str:
    import hashlib

    return hashlib.sha1(f"demo:{vacante_id}:{nombre}".encode("utf-8")).hexdigest()[:32]


# -------------------------------------------------------------- extra estados
ESTADOS_EXTRA = {
    "ANALISTA DE DATOS": [
        dict(
            nombre="LETICIA MERCEDES QUISPE FLORES", email="leticia.q@hotmail.com",
            telefono="51951234567",
            habilidades=["Excel", "Office", "Trabajo en equipo"],
            estado="Pendiente: Reintento IA",
            texto_crudo="Hoja de vida en formato escaneado sin OCR... Leticia Mercedes Quispe Flores. Reconocimientos.",
        ),
    ],
    "EJECUTIVO COMERCIAL": [
        dict(
            nombre="HUGO RICARDO BRAVO SALAZAR", email="hugo.bravo@outlook.com",
            telefono="51958765432",
            habilidades=["Ventas", "Negociación"],
            estado="Error: Archivo Ilegible",
            motivo="El PDF adjunto no pudo procesarse: archivo corrupto.",
        ),
    ],
    "DESARROLLADOR BACKEND": [
        dict(
            nombre="INES RAQUEL CHAVEZ MENDOZA", email="ines.chavez@gmail.com",
            telefono="51957778899",
            habilidades=["Python", "Git"],
            estado="Listo para Evaluación",
        ),
    ],
}

_EXTRA_N = 0


def _extra(vacante_id: str, entry: dict) -> None:
    global _EXTRA_N
    _EXTRA_N += 1
    id_cand = _id_para("EXTRA", f"{vacante_id}:{_EXTRA_N}")[:32]
    estado = entry.get("estado", "Listo para Evaluación")
    _silver(
        vacante_id,
        id_cand,
        entry["nombre"],
        entry["email"],
        entry["telefono"],
        entry["habilidades"],
        [],
        [],
        estado,
        motivo=entry.get("motivo"),
        texto_crudo=entry.get("texto_crudo"),
    )


# --------------------------------------------------------------------- vuelve
def _recalcular_ranking_con_telefono() -> None:
    """Reconstruye ranking.json incluyendo telefono (para la vista fase técnica)."""
    evaluacion = DIR_DEMO / "gold" / "evaluacion"
    for carpeta in sorted(evaluacion.iterdir()):
        if not carpeta.is_dir():
            continue
        filas: list[dict] = []
        for ruta in sorted(carpeta.glob("*.json")):
            if ruta.name == NOMBRE_RANKING:
                continue
            doc = json.loads(ruta.read_text(encoding="utf-8"))
            if not isinstance(doc.get("match_score"), (int, float)):
                continue
            filas.append(
                {
                    "vacante_id": doc.get("vacante_id"),
                    "id_candidato": doc.get("id_candidato"),
                    "nombre": doc.get("nombre_completo"),
                    "email_remitente": doc.get("email_remitente"),
                    "telefono": doc.get("telefono"),
                    "match_score": round(float(doc["match_score"]), 2),
                    "clasificacion": doc.get("clasificacion"),
                    "fecha_evaluacion": doc.get("fecha_evaluacion"),
                }
            )
        filas.sort(key=lambda f: f["match_score"], reverse=True)
        (carpeta / NOMBRE_RANKING).write_text(
            json.dumps(
                {
                    "vacante_id": filas[0]["vacante_id"] if filas else carpeta.name,
                    "total": len(filas),
                    "candidatos": filas,
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )


# ------------------------------------------------------------------- roster
def generar() -> int:
    import shutil

    if DIR_DEMO.exists():
        shutil.rmtree(DIR_DEMO)
    DIR_DEMO.mkdir(parents=True, exist_ok=True)

    conteo: dict[str, dict[str, int]] = {}

    for vacante_id, candidatos in ROSTER.items():
        requisitos = _leer_requisitos(vacante_id)
        for datos in candidatos:
            fila = _candidato(vacante_id, requisitos, **datos)
            c = conteo.setdefault(
                fila["vacante_id"],
                {"Alta": 0, "Media": 0, "Baja": 0, "evaluados": 0, "silver": 0},
            )
            c[_clasificar(fila["score"])] += 1
            c["evaluados"] += 1

    for vacante_id, extras in ESTADOS_EXTRA.items():
        for entry in extras:
            _extra(vacante_id, entry)
        conteo.setdefault(vacante_id, {"Alta": 0, "Media": 0, "Baja": 0, "evaluados": 0, "silver": 0})

    _recalcular_ranking_con_telefono()

    total_extra = sum(len(v) for v in ESTADOS_EXTRA.values())
    total_silver = sum(c["evaluados"] for c in conteo.values()) + total_extra
    print(f"Datos demo generados en {DIR_DEMO} ({total_silver} candidatos silver, "
          f"{sum(c['evaluados'] for c in conteo.values())} evaluados).")
    for vacante_id, c in conteo.items():
        print(f"  {vacante_id:<24} Alta={c['Alta']} Media={c['Media']} Baja={c['Baja']}")
    print("Para probar localmente:")
    print("  DATA_DIR=data_demo uv run python main.py chat --port 8510")
    return 0


F_ANALISTA = "2026-09-05T09:00:00-05:00"
F_COMERCIAL = "2026-09-04T09:00:00-05:00"
F_BACKEND = "2026-09-03T09:00:00-05:00"

ROSTER: dict[str, list[dict]] = {
    "ANALISTA DE DATOS": [
        dict(nombre="ANA MARIA GOMEZ QUISPE", email="ana.gomez@gmail.com",
             telefono="51991234561", n_esc=6, cnt_opt=3, exp_anos=4.0, exp_p=90,
             form_p=90, formaciones=[dict(grado="Titulada", carrera="Ingeniería de Sistemas",
             institucion="Universidad Nacional de Ingeniería")], fecha_envio=F_ANALISTA),
        dict(nombre="DIEGO ANTONIO SALAZAR LUNA", email="diego.salazar@hotmail.com",
             telefono="51992345672", n_esc=6, cnt_opt=2, exp_anos=3.5, exp_p=80,
             form_p=80, formaciones=[dict(grado="Bachiller", carrera="Ingeniería de Datos",
             institucion="Universidad Nacional Mayor de San Marcos")], fecha_envio=F_ANALISTA),
        dict(nombre="CARLA PAOLA VEGA SOTO", email="carla.vega@outlook.com",
             telefono="51993456783", n_esc=6, cnt_opt=1, exp_anos=2.0, exp_p=65,
             form_p=70, formaciones=[dict(grado="Bachiller", carrera="Estadística",
             institucion="Universidad Nacional Mayor de San Marcos"), dict(grado="Curso",
             carrera="Business Intelligence", institucion="Coursera")], fecha_envio=F_ANALISTA),
        dict(nombre="RENATO JORGE PALACIOS RIVERA", email="renato.palacios@gmail.com",
             telefono="51994567894", n_esc=5, cnt_opt=3, exp_anos=5.0, exp_p=85,
             form_p=75, formaciones=[dict(grado="Titulado", carrera="Ingeniería de Sistemas",
             institucion="PUCP")], fecha_envio=F_ANALISTA),
        dict(nombre="MARIA FERNANDA ALVAREZ DIAZ", email="maria.alvarez@yahoo.com",
             telefono="51995678905", n_esc=5, cnt_opt=0, exp_anos=1.5, exp_p=55,
             form_p=65, formaciones=[dict(grado="Estudiante (9no ciclo)",
             carrera="Ingeniería de Sistemas", institucion="UNFV")], fecha_envio=F_ANALISTA),
        dict(nombre="GUSTAVO ADOLFO ROMERO CARRASCO", email="gustavo.romero@gmail.com",
             telefono="51996789016", n_esc=4, cnt_opt=3, exp_anos=3.0, exp_p=70,
             form_p=70, formaciones=[dict(grado="Bachiller", carrera="Ciencias de la Computación",
             institucion="UTEC")], fecha_envio=F_ANALISTA),
        dict(nombre="PATRICIA SOLEDAD MARCELO CORDOVA", email="patricia.marcelo@hotmail.com",
             telefono="51997890127", n_esc=4, cnt_opt=1, exp_anos=2.0, exp_p=60,
             form_p=60, formaciones=[dict(grado="Bachiller", carrera="Administración",
             institucion="Universidad de Lima")], fecha_envio=F_ANALISTA),
        dict(nombre="JOSE LUIS INFANTES CORONADO", email="jose.infantes@outlook.com",
             telefono="51998901238", n_esc=3, cnt_opt=2, exp_anos=1.0, exp_p=45,
             form_p=55, formaciones=[dict(grado="Técnico", carrera="Computación e Informática",
             institucion="TECSUP")], fecha_envio=F_ANALISTA),
        dict(nombre="ROSA ELENA FLORES PAZ", email="rosa.flores@gmail.com",
             telefono="51990123409", n_esc=3, cnt_opt=0, exp_anos=0.5, exp_p=35,
             form_p=40, formaciones=[dict(grado="Estudiante (5to ciclo)",
             carrera="Ingeniería Industrial", institucion="UNMSM")], fecha_envio=F_ANALISTA),
        dict(nombre="MIKE ANDERSON BUSTAMANTE SANCHEZ", email="mike.bustamante@yahoo.com",
             telefono="51991234510", n_esc=2, cnt_opt=1, exp_anos=1.0, exp_p=30,
             form_p=35, formaciones=[dict(grado="Bachiller", carrera="Derecho",
             institucion="UNFV")], fecha_envio=F_ANALISTA),
    ],
    "EJECUTIVO COMERCIAL": [
        dict(nombre="PEDRO MANUEL CASTRO VILLANUEVA", email="pedro.castro@gmail.com",
             telefono="51992345621", n_esc=6, cnt_opt=4, exp_anos=6.0, exp_p=95,
             form_p=85, formaciones=[dict(grado="Titulado", carrera="Administración",
             institucion="ESAN")], fecha_envio=F_COMERCIAL),
        dict(nombre="MERCEDES ALEXANDRA TAPIA RODAS", email="mercedes.tapia@hotmail.com",
             telefono="51993456732", n_esc=6, cnt_opt=3, exp_anos=4.5, exp_p=85,
             form_p=85, formaciones=[dict(grado="Bachiller", carrera="Marketing",
             institucion="Universidad de Lima")], fecha_envio=F_COMERCIAL),
        dict(nombre="FERNANDO RAUL MONTERO ABANTO", email="fernando.montero@outlook.com",
             telefono="51994567843", n_esc=6, cnt_opt=2, exp_anos=3.0, exp_p=75,
             form_p=80, formaciones=[dict(grado="Bachiller", carrera="Economía",
             institucion="Universidad Nacional de Ingeniería"), dict(grado="Diplomado",
             carrera="Gestión Comercial", institucion="ESAN")], fecha_envio=F_COMERCIAL),
        dict(nombre="EVELYN NICOLE ORTIZ BARRANTES", email="evelyn.ortiz@gmail.com",
             telefono="51995678954", n_esc=5, cnt_opt=3, exp_anos=3.5, exp_p=80,
             form_p=75, formaciones=[dict(grado="Bachiller", carrera="Ingeniería Comercial",
             institucion="Universidad Católica San Pablo")], fecha_envio=F_COMERCIAL),
        dict(nombre="JORGE ENRIQUE MEZA QUISPE", email="jorge.meza@yahoo.com",
             telefono="51996789065", n_esc=5, cnt_opt=1, exp_anos=2.5, exp_p=65,
             form_p=60, formaciones=[dict(grado="Estudiante (10mo ciclo)",
             carrera="Administración", institucion="USIL")], fecha_envio=F_COMERCIAL),
        dict(nombre="VANESSA ANDREA VARGAS SAAVEDRA", email="vanessa.vargas@gmail.com",
             telefono="51997890176", n_esc=4, cnt_opt=2, exp_anos=3.0, exp_p=70,
             form_p=65, formaciones=[dict(grado="Bachiller", carrera="Comunicaciones",
             institucion="Universidad de Lima")], fecha_envio=F_COMERCIAL),
        dict(nombre="OSCAR FIDEL CAMACHO HUAYTA", email="oscar.camacho@hotmail.com",
             telefono="51998901287", n_esc=4, cnt_opt=0, exp_anos=2.0, exp_p=55,
             form_p=55, formaciones=[dict(grado="Técnico", carrera="Marketing Digital",
             institucion="Instituto Certus")], fecha_envio=F_COMERCIAL),
        dict(nombre="KELLY MARGARITA SANDOVAL CHUMPITAZ", email="kelly.sandoval@outlook.com",
             telefono="51990123498", n_esc=3, cnt_opt=2, exp_anos=1.5, exp_p=45,
             form_p=50, formaciones=[dict(grado="Estudiante (8vo ciclo)",
             carrera="Administración", institucion="UTP")], fecha_envio=F_COMERCIAL),
        dict(nombre="ANDRES MARTIN PELAEZ MONTENEGRO", email="andres.pelaez@gmail.com",
             telefono="51991234519", n_esc=3, cnt_opt=0, exp_anos=1.0, exp_p=35,
             form_p=40, formaciones=[dict(grado="Bachiller", carrera="Psicología",
             institucion="PUCP")], fecha_envio=F_COMERCIAL),
        dict(nombre="SILVIA ELIANA CABRERA AGUIRRE", email="silvia.cabrera@yahoo.com",
             telefono="51992345620", n_esc=2, cnt_opt=0, exp_anos=0.5, exp_p=25,
             form_p=35, formaciones=[dict(grado="Estudiante (3er ciclo)",
             carrera="Derecho", institucion="UNMSM")], fecha_envio=F_COMERCIAL),
    ],
    "DESARROLLADOR BACKEND": [
        dict(nombre="ALVARO RICARDO PACHECO GUILLEN", email="alvaro.pacheco@gmail.com",
             telefono="51993456731", n_esc=6, cnt_opt=4, exp_anos=4.0, exp_p=90,
             form_p=90, formaciones=[dict(grado="Titulado", carrera="Ingeniería de Software",
             institucion="PUCP")], fecha_envio=F_BACKEND),
        dict(nombre="NADIA SOFIA ZAVALA RICALDI", email="nadia.zavala@hotmail.com",
             telefono="51994567842", n_esc=6, cnt_opt=3, exp_anos=3.0, exp_p=80,
             form_p=85, formaciones=[dict(grado="Bachiller", carrera="Ciencias de la Computación",
             institucion="Universidad Nacional de Ingeniería")], fecha_envio=F_BACKEND),
        dict(nombre="CRISTHIAN PAUL JIMENEZ LAZO", email="cristhian.jimenez@outlook.com",
             telefono="51995678953", n_esc=6, cnt_opt=1, exp_anos=1.5, exp_p=60,
             form_p=75, formaciones=[dict(grado="Bachiller", carrera="Ingeniería Informática",
             institucion="Universidad Nacional Federico Villarreal"), dict(grado="Curso",
             carrera="AWS Practitioner", institucion="AWS")], fecha_envio=F_BACKEND),
        dict(nombre="SANDRA ISABEL CUEVA RAMOS", email="sandra.cueva@gmail.com",
             telefono="51996789064", n_esc=5, cnt_opt=3, exp_anos=2.5, exp_p=70,
             form_p=80, formaciones=[dict(grado="Bachiller", carrera="Ingeniería de Sistemas",
             institucion="UNI")], fecha_envio=F_BACKEND),
        dict(nombre="EMILIO JAVIER MOLINA ARCE", email="emilio.molina@yahoo.com",
             telefono="51997890175", n_esc=5, cnt_opt=2, exp_anos=2.0, exp_p=65,
             form_p=70, formaciones=[dict(grado="Estudiante (9no ciclo)",
             carrera="Ingeniería de Software", institucion="UTEC")], fecha_envio=F_BACKEND),
        dict(nombre="PAOLA CRISTINA MELENDEZ PALOMINO", email="paola.melendez@gmail.com",
             telefono="51998901286", n_esc=4, cnt_opt=3, exp_anos=1.0, exp_p=55,
             form_p=65, formaciones=[dict(grado="Bachiller", carrera="Ingeniería Informática",
             institucion="UNFV")], fecha_envio=F_BACKEND),
        dict(nombre="WALTER EFRAIN QUISPE MANRIQUE", email="walter.quispe@hotmail.com",
             telefono="51990123497", n_esc=4, cnt_opt=1, exp_anos=3.0, exp_p=70,
             form_p=60, formaciones=[dict(grado="Técnico", carrera="Computación e Informática",
             institucion="Senati"), dict(grado="Curso", carrera="Backend con Python",
             institucion="Platzi")], fecha_envio=F_BACKEND),
        dict(nombre="NATALY FABIOLA HUAMAN GONZALES", email="nataly.huaman@outlook.com",
             telefono="51991234518", n_esc=3, cnt_opt=2, exp_anos=0.5, exp_p=40,
             form_p=55, formaciones=[dict(grado="Estudiante (7mo ciclo)",
             carrera="Ingeniería de Sistemas", institucion="UNMSM")], fecha_envio=F_BACKEND),
        dict(nombre="EDUARDO ANTONY SAAVEDRA VILCA", email="eduardo.saavedra@gmail.com",
             telefono="51992345629", n_esc=3, cnt_opt=0, exp_anos=1.0, exp_p=35,
             form_p=45, formaciones=[dict(grado="Bachiller", carrera="Ingeniería Mecatrónica",
             institucion="UNI")], fecha_envio=F_BACKEND),
        dict(nombre="CINTHYA LIZETT BERNUY MALDONADO", email="cinthya.beruy@yahoo.com",
             telefono="51993456730", n_esc=2, cnt_opt=1, exp_anos=0.5, exp_p=30,
             form_p=35, formaciones=[dict(grado="Estudiante (4to ciclo)",
             carrera="Ingeniería Ambiental", institucion="UNALM")], fecha_envio=F_BACKEND),
    ],
}


if __name__ == "__main__":
    raise SystemExit(generar())