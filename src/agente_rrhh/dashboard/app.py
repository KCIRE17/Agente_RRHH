"""FASE 3 — Dashboard Streamlit del Agente RRHH.

Vistas (en lenguaje del área de talento):
    * Ranking      — ranking por vacante, filtrable por compatibilidad.
    * Postulante   — ficha con contacto, fortalezas, aspectos por reforzar,
      puntaje y hoja de vida.
    * Postulaciones — resumen de lo recibido y su situación.
    * Metodología  — cómo se calcula el puntaje y qué significa cada estado.

Arranque: `uv run python main.py dashboard` (punto de entrada único).
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import streamlit as st

_RUTA_RAIZ = Path(__file__).resolve().parent.parent.parent.parent
if str(_RUTA_RAIZ) not in sys.path:
    sys.path.insert(0, str(_RUTA_RAIZ))

from src.agente_rrhh.dashboard import consultas

ESTADOS_COLOR = consultas.ESTADOS_COLOR
CLASIFICACIONES = ["Alta", "Media", "Baja"]
COMPATIBILIDAD = {
    "Compatibilidad alta": "Alta",
    "Compatibilidad media": "Media",
    "Compatibilidad baja": "Baja",
}
LABEL_COMPATIBILIDAD = {v: k for k, v in COMPATIBILIDAD.items()}

st.set_page_config(
    page_title="Agente RRHH · Dashboard",
    page_icon=":bar_chart:",
    layout="wide",
    initial_sidebar_state="expanded",
)

_CSS = """
<style>
[data-testid="stMetric"] {
    background: #f8fafc;
    border: 1px solid #e2e8f0;
    border-radius: 12px;
    padding: 12px 16px;
}
div[data-testid="stMetricLabel"] p { font-size: 0.85rem; }
.badge { padding: 2px 10px; border-radius: 999px; color: white;
         font-weight: 700; display: inline-block; }
.puntuacion { font-size: 2.4rem; font-weight: 800; line-height: 1; }
.ficha-contacto { font-size: 1.05rem; }
.habilidad { display: inline-block; background: #eff6ff; color: #1d4ed8;
             border: 1px solid #bfdbfe; border-radius: 999px;
             padding: 2px 10px; margin: 2px 4px 2px 0; font-size: 0.85rem; }
</style>
"""
st.markdown(_CSS, unsafe_allow_html=True)


def _etiqueta_clasificacion(clasificacion: str) -> str:
    return LABEL_COMPATIBILIDAD.get(clasificacion, clasificacion)


def _badge_clasificacion(clasificacion: str) -> str:
    color = ESTADOS_COLOR.get(clasificacion, "#64748b")
    return (
        f'<span class="badge" style="background:{color}">'
        f"{_etiqueta_clasificacion(clasificacion)}</span>"
    )


@st.cache_data(ttl=30, show_spinner="Cargando datos locales…")
def _vacantes_cargar(gold_dir: str) -> list[dict]:
    return consultas.listar_vacantes_con_ranking(gold_dir)


@st.cache_data(ttl=30, show_spinner=False)
def _ranking_cargar(gold_dir: str, carpeta: str) -> tuple[str, list[dict]]:
    return consultas.ranking_vacante(gold_dir, carpeta)


@st.cache_data(ttl=30, show_spinner=False)
def _detalle_cargar(
    gold_dir: str, silver_dir: str, carpeta: str, id_candidato: str
) -> dict | None:
    return consultas.detalle_candidato(gold_dir, silver_dir, carpeta, id_candidato)


@st.cache_data(ttl=30, show_spinner=False)
def _ingesta_cargar(silver_dir: str, gold_dir: str) -> dict:
    return consultas.resumen_ingesta(silver_dir, gold_dir)


def render_ranking(vacantes: list[dict], gold_dir: str) -> None:
    carpetas = {v["vacante_id"]: v["carpeta"] for v in vacantes}
    vacante = st.selectbox("Vacante", list(carpetas.keys()), key="vacante_ranking")
    carpeta = carpetas[vacante]
    vacante_id, filas = _ranking_cargar(gold_dir, carpeta)

    st.header(f"Ranking de postulantes · {vacante_id}")
    col_f, col_a, col_m, col_b, col_p = st.columns(5)
    total = len(filas)
    df = pd.DataFrame(filas)
    col_f.metric("Postulantes evaluados", total)
    if total:
        col_p.metric("Puntaje promedio", f"{df['match_score'].mean():.1f}")
        col_a.metric(
            "Compatibilidad alta", (df["clasificacion"] == "Alta").sum()
        )
        col_m.metric("Compatibilidad media", (df["clasificacion"] == "Media").sum())
        col_b.metric("Compatibilidad baja", (df["clasificacion"] == "Baja").sum())
    else:
        col_p.metric("Puntaje promedio", "0.0")

    if total == 0:
        st.info("Aún no hay postulantes evaluados para esta vacante.")
        return

    clases = sorted({c for c in CLASIFICACIONES if c in set(df["clasificacion"])})
    etiquetas = [_etiqueta_clasificacion(c) for c in clases]
    seleccion = st.multiselect(
        "Filtrar por compatibilidad",
        options=etiquetas,
        default=etiquetas,
        label_visibility="collapsed",
    )
    activas = {COMPATIBILIDAD[etiqueta] for etiqueta in seleccion}
    df = df[df["clasificacion"].isin(activas)].copy()

    tabla = df[["posicion", "nombre", "match_score", "clasificacion", "email_remitente"]]
    tabla = tabla.rename(
        columns={
            "posicion": "#",
            "nombre": "Postulante",
            "match_score": "Puntaje",
            "clasificacion": "Compatibilidad",
            "email_remitente": "Correo",
        }
    )
    st.dataframe(
        tabla,
        width="stretch",
        hide_index=True,
        column_config={
            "Puntaje": st.column_config.ProgressColumn(
                "Puntaje", min_value=0, max_value=100, format="%.0f"
            ),
            "Compatibilidad": st.column_config.TextColumn("Compatibilidad"),
            "Correo": st.column_config.Column(width="large"),
        },
    )

    st.subheader("Postulantes por nivel de compatibilidad")
    distribucion = pd.DataFrame(
        {
            "Nivel": [_etiqueta_clasificacion(c) for c in clases],
            "Postulantes": [
                int((df["clasificacion"] == c).sum()) for c in clases
            ],
        }
    ).set_index("Nivel")
    if not distribucion.empty:
        st.bar_chart(distribucion, height=260)


def render_ficha(vacantes: list[dict], gold_dir: str, silver_dir: str) -> None:
    carpetas = {v["vacante_id"]: v["carpeta"] for v in vacantes}
    vacante = st.selectbox("Vacante", list(carpetas.keys()), key="vacante_ficha")
    carpeta = carpetas[vacante]
    _, filas = _ranking_cargar(gold_dir, carpeta)
    if not filas:
        st.info("Aún no hay postulantes evaluados para esta vacante.")
        return
    opciones = {f"{f['nombre']} · {f['match_score']:.0f}": f for f in filas}
    seleccion = st.selectbox("Postulante", list(opciones.keys()), key="candidato_ficha")
    fila = opciones[seleccion]
    doc = _detalle_cargar(gold_dir, silver_dir, carpeta, fila["id_candidato"])
    if doc is None:
        st.error("No se pudo cargar la información de este postulante.")
        return

    st.header("Ficha del postulante")
    col_score, col_clas, col_contacto = st.columns([1, 1, 2])
    col_score.markdown(
        f'<div class="puntuacion">{doc.get("match_score", "—")}</div>'
        "<small>Puntaje de compatibilidad (0–100)</small>",
        unsafe_allow_html=True,
    )
    col_clas.markdown(
        _badge_clasificacion(str(doc.get("clasificacion", "—")))
        + "<br><small>nivel de compatibilidad</small>",
        unsafe_allow_html=True,
    )
    email = doc.get("email_remitente") or "—"
    telefono = doc.get("telefono") or "—"
    col_contacto.markdown(
        '<div class="ficha-contacto">'
        f"<b>{doc.get('nombre_completo') or '—'}</b><br>"
        f"📞 {telefono}<br>"
        f"✉️ <a href='mailto:{email}'>{email}</a></div>",
        unsafe_allow_html=True,
    )

    sugerencia = consultas.sugerencia_clasificacion(doc.get("clasificacion") or "")
    color = ESTADOS_COLOR.get(doc.get("clasificacion"), "#64748b")
    st.markdown(
        f'<div style="border:2px solid {color};border-radius:12px;padding:12px 16px">'
        f"<b style='color:{color}'>Sugerencia: {sugerencia['titulo']}</b><br>"
        f"{sugerencia['descripcion']} "
        f"{_badge_clasificacion(str(doc.get('clasificacion', '')))}"
        "</div>",
        unsafe_allow_html=True,
    )

    col_fort, col_br = st.columns(2)
    con_fort = col_fort.container(border=True)
    con_fort.subheader("Fortalezas")
    fortalezas = doc.get("fortalezas") or []
    if fortalezas:
        for item in fortalezas:
            con_fort.markdown(f"- {item}")
    else:
        con_fort.caption("Sin fortalezas registradas.")

    con_br = col_br.container(border=True)
    con_br.subheader("Aspectos por reforzar")
    brechas = doc.get("brechas") or []
    ausentes = doc.get("requisito_esencial_ausente") or []
    for item in brechas:
        con_br.markdown(f"- {item}")
    for item in ausentes:
        con_br.error(f"Falta un requisito indispensable: {item}")
    if not brechas and not ausentes:
        con_br.caption("Sin aspectos por reforzar para el puesto.")

    justificacion = doc.get("justificacion")
    if justificacion:
        st.subheader("Resumen del análisis")
        st.write(justificacion)

    st.subheader("¿Cómo se calculó el puntaje?")
    st.caption("Habilidades 50 % · Experiencia 30 % · Formación 20 %")
    puntos = doc.get("puntos_por_bloque") or {}
    if puntos:
        desglose = pd.DataFrame(
            puntos.items(), columns=["Componente", "Puntos"]
        ).set_index("Componente")
        izq, der = st.columns([1, 2])
        izq.table(desglose)
        der.bar_chart(desglose, height=220)

    _render_hoja_de_vida(doc.get("silver"))


def _render_hoja_de_vida(silver: dict | None) -> None:
    st.subheader("Resumen de la hoja de vida")
    st.caption("Información extraída automáticamente de la hoja de vida.")
    if not silver:
        st.caption("No se encontró la hoja de vida del postulante.")
        return
    datos = silver.get("datos_json") or {}
    estructurados = datos.get("datos_estructurados") or {}

    habilidades = estructurados.get("habilidades") or []
    if habilidades:
        chips = "".join(f'<span class="habilidad">{h}</span>' for h in habilidades)
        st.write(f"**Conocimientos y habilidades** &nbsp; {chips}", unsafe_allow_html=True)

    experiencia = estructurados.get("experiencia_laboral") or []
    formacion = estructurados.get("formacion_academica") or []
    certificaciones = estructurados.get("certificaciones") or []

    if experiencia:
        with st.expander(f"Experiencia laboral ({len(experiencia)})", expanded=False):
            for e in experiencia:
                st.markdown(
                    f"**{e.get('puesto', '—')}** · {e.get('duracion_anos', '—')} años"
                    if e.get("duracion_anos")
                    else f"**{e.get('puesto', '—')}**"
                )
                if e.get("descripcion"):
                    st.caption(e["descripcion"])
    if formacion:
        with st.expander(f"Formación académica ({len(formacion)})", expanded=False):
            for f in formacion:
                st.markdown(
                    f"{f.get('grado', '—')} · {f.get('carrera', '—')} · "
                    f"{f.get('institucion', '—')}"
                )
    if certificaciones:
        st.write(
            f"**Certificaciones:** {', '.join(str(c) for c in certificaciones)}"
        )
    if not (habilidades or experiencia or formacion or certificaciones):
        st.caption("No se pudo extraer información de la hoja de vida.")


def render_postulaciones(silver_dir: str, gold_dir: str) -> None:
    st.header("Postulaciones recibidas")
    resumen = _ingesta_cargar(silver_dir, gold_dir)
    total = resumen["total_silver"]
    st.metric("Postulaciones recibidas", total)
    if total == 0:
        st.info("Aún no hay postulaciones registradas.")
        return

    por_estado = resumen["por_estado"]
    df_estado = pd.DataFrame(
        [{"Situación": e, "Postulantes": c} for e, c in sorted(por_estado.items())]
    )
    st.subheader("Situación de las postulaciones")
    st.dataframe(df_estado, width="stretch", hide_index=True)

    st.subheader("Postulaciones por vacante")
    por_vacante = resumen["por_vacante"]
    df_vac = pd.DataFrame(
        [
            {
                "Vacante": v,
                "Postulantes": r["total"],
                "Evaluados": r["evaluados"],
                "Por evaluar": r["listos"],
                "Incidencias": r["errores"] + r["reintentos"],
            }
            for v, r in sorted(por_vacante.items())
        ]
    )
    st.dataframe(df_vac, width="stretch", hide_index=True)

    evaluadas = consultas.vacantes_evaluadas(gold_dir)
    from src.agente_rrhh.core.vacantes import slug_vacante

    pendientes = sorted(
        v
        for v, r in por_vacante.items()
        if slug_vacante(v) not in evaluadas and r["listos"] > 0
    )
    if pendientes:
        st.warning(
            "Hay postulaciones pendientes de evaluación en: "
            + ", ".join(pendientes)
            + "."
        )


def render_metodologia() -> None:
    st.header("Metodología")
    st.markdown(
        "El sistema compara de forma automática cada hoja de vida con los "
        "requisitos de la vacante. Esto es lo que debes saber para leer el "
        "panel."
    )

    st.subheader("Cómo funciona el proceso")
    for num, titulo, texto in [
        (
            "1",
            "Llega la postulación",
            "El candidato envía su hoja de vida al correo de postulaciones.",
        ),
        (
            "2",
            "Se extrae la información",
            "Se leen las habilidades, la experiencia, la formación y las "
            "certificaciones de la hoja de vida.",
        ),
        (
            "3",
            "Se compara con la vacante",
            "La información se contrasta con los requisitos definidos "
            "para cada puesto.",
        ),
        (
            "4",
            "Se obtiene el puntaje y la sugerencia",
            "El resultado es un puntaje de compatibilidad (0–100) y una "
            "recomendación para el área.",
        ),
    ]:
        st.markdown(f"**{num}. {titulo}** — {texto}")

    st.subheader("¿Cómo se calcula el puntaje?")
    st.markdown(
        "- **Habilidades y conocimientos (50 %):** herramientas, idiomas y "
        "competencias del candidato.\n"
        "- **Experiencia (30 %):** años y puestos previos relacionados con "
        "la vacante.\n"
        "- **Formación (20 %):** carreras y estudios afines.\n\n"
        "El puntaje final lo calcula una **regla fija** a partir de esos tres "
        "componentes (un modelo de IA configurable colabora en el análisis de "
        "las hojas de vida)."
    )

    st.subheader("Niveles de compatibilidad")
    st.markdown(
        "| Nivel | Puntaje | Qué significa |\n"
        "| :--- | :---: | :--- |\n"
        "| **Compatibilidad alta** | 80–100 | Muy buena afinidad con el "
        "puesto. Avanza a entrevista o prueba técnica. |\n"
        "| **Compatibilidad media** | 50–79 | Buena base, pero amerita "
        "revisión manual antes de decidir. |\n"
        "| **Compatibilidad baja** | Menos de 50 | Poca afinidad con la "
        "vacante. No avanza en el proceso. |"
    )

    st.subheader("Una evaluación objetiva")
    st.markdown(
        "Para evitar sesgos, **nunca** se usan la foto, la edad, el género, "
        "la dirección ni el estado civil. Solo influyen las habilidades, la "
        "experiencia y la formación."
    )

    st.subheader("Situaciones de una postulación")
    explicaciones = {
        "Pendiente de evaluación": "La hoja de vida llegó correctamente y "
        "está en cola para compararse con la vacante.",
        "Evaluado": "Ya tiene puntaje de compatibilidad y sugerencia.",
        "Documento no legible": "No se pudo leer el archivo enviado, por "
        "ejemplo una hoja escaneada como imagen.",
        "Formato no permitido": "El archivo no es de un tipo admitido "
        "(PDF, Word o texto).",
        "En espera de nuevo intento": "Hubo un inconveniente temporal con el "
        "análisis; se volverá a intentar.",
        "Pendiente de re-evaluación": "La comparación falló temporalmente "
        "y se reintentará.",
    }
    for situacion in consultas.ESTADOS_AMIGABLES.values():
        explicacion = explicaciones.get(situacion, situacion)
        st.markdown(f"- **{situacion}:** {explicacion}")

    st.info(
        "Si necesitas ajustar los requisitos de una vacante, son editables "
        "sin depender del sistema (el área define qué busca en cada puesto)."
    )


def main() -> None:
    st.title("Agente RRHH · Preselección de talento")
    st.caption("Panel del área de talento — postulantes, evaluaciones y recomendaciones.")

    with st.sidebar:
        st.header("Panel")
        if st.button("Actualizar información", width="stretch"):
            st.cache_data.clear()
            st.cache_resource.clear()

    cfg = _config()
    vacantes = _vacantes_cargar(cfg.gold_dir)
    if not vacantes:
        st.info(
            "Aún no hay postulantes evaluados. En cuanto el sistema procese "
            "postulaciones, los resultados aparecerán aquí."
        )
        render_postulaciones(cfg.silver_dir, cfg.gold_dir)
        render_metodologia()
        return

    pestaña = st.tabs(
        ["Ranking", "Postulante", "Postulaciones", "Metodología"]
    )
    with pestaña[0]:
        render_ranking(vacantes, cfg.gold_dir)
    with pestaña[1]:
        render_ficha(vacantes, cfg.gold_dir, cfg.silver_dir)
    with pestaña[2]:
        render_postulaciones(cfg.silver_dir, cfg.gold_dir)
    with pestaña[3]:
        render_metodologia()


@st.cache_resource(show_spinner=False)
def _config() -> "Config":
    from src.agente_rrhh.core.config import Config

    return Config.desde_env()


main()