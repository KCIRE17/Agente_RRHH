"""Motor del chatbot F4: respuestas en codigo (modo offline, costo $0).

Las 8 utilidades se resuelven con datos de silver/gold y la fachada
``dashboard.consultas``. Los elementos visuales (tablas, tarjetas, listas) se
construyen aqui sin llamar a la IA. Si ``PROVEEDOR_CHAT`` esta configurado en
.env (y hay clave), se enriquece la *narrativa* de la respuesta con el LLM,
pero los bloques visuales nunca dependen de el (0 tokens en modo offline).
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from ..core import costo as costo_mod
from ..core.llm import ErrorModelo
from ..core.prompts import cargar_prompt
from . import datos, simulador
from .sesion import Sesion

LOG = logging.getLogger("agente_rrhh")

_NORM = str.maketrans("ÁÉÍÓÚÜÑ", "AEIOUUN")
_RUTA_PROMPT_CHAT = Path(__file__).resolve().parents[3] / "prompt" / "chatbot.md"

_CLASE = {"Alta": "alta", "Media": "media", "Baja": "baja"}
_STOP_NOMBRES = {"DE", "DEL", "Y", "LA", "LAS", "EL", "LOS", "SAN", "VON", "DA", "DO", "EN"}


def normalizar(texto: str) -> str:
    return (texto or "").upper().translate(_NORM).strip()


def _celda(texto: Any, clase: str | None = None) -> Any:
    return {"texto": str(texto), "clase": clase} if clase else str(texto)


def _nombre_tokens(nombre: str) -> list[str]:
    """Tokens relevantes de un nombre (>= 3 letras, sin articulos/preposiciones)."""
    return [
        t
        for t in normalizar(nombre).split()
        if len(t) >= 3 and t not in _STOP_NOMBRES
    ]


class MotorChat:
    def __init__(self, cfg: Any) -> None:
        self._cfg = cfg

    # ------------------------------------------------------------ publico
    def resolver(self, mensaje: str, sesion: Sesion) -> dict[str, Any]:
        pregunta = (mensaje or "").strip()
        intencion, contexto = self._clasificar(pregunta, sesion)
        respuesta = self._ejecutar(intencion, pregunta, contexto, sesion)
        respuesta["intencion"] = intencion
        respuesta["sesion"] = sesion.resumen()
        self._aplicar_ia_opcional(sesion, pregunta, respuesta)
        respuesta["ia_restantes"] = sesion.ia_restantes
        return respuesta

    # ------------------------------------------------------- clasificacion
    def _clasificar(self, texto: str, sesion: Sesion) -> tuple[str, dict[str, Any]]:
        n = normalizar(texto)
        ctx: dict[str, Any] = {}

        def menciona_nombre() -> bool:
            for e in datos.docs_evaluados(self._cfg):
                nombre = normalizar(e["fila"]["nombre"])
                if not nombre:
                    continue
                if nombre in n or any(t in n for t in _nombre_tokens(nombre)):
                    return True
            return False

        if not n:
            return "ayuda", ctx
        if any(p in n for p in ("NUEVO CHAT", "REINICIAR", "RESET", "LIMPIAR CHAT")):
            return "reiniciar", ctx
        if n in {"HOLA", "HOLA!", "BUENOS DIAS", "HOLA BUENAS", "HEY", "HI"} or (
            n.startswith("HOLA") and len(n.split()) <= 3
        ):
            return "saludo", ctx
        if any(p in n for p in ("AYUDA", "QUE PUEDES", "QUE PUEDO", "OPCIONES", "MENU", "FUNCIONES", "QUE HACES", "COMO SE USA")):
            return "ayuda", ctx
        if any(p in n for p in ("COSTO", "GASTO", "GASTOS", "GASTADO", "TOKENS", "CUENTA", "FACTUR", "DINERO", "PRECIO")):
            return "costos", ctx
        if any(p in n for p in ("COMPARA", "COMPARAR", "COMPARACION", "COMPARE", "VERSUS", "DIFERENCIA")):
            return "comparar", ctx
        if any(p in n for p in ("ORIGEN", "DOMINIO", "GMAIL", "HOTMAIL", "CANAL", "FUENTE", "DONDE VIENEN", "RECLUTAMIENTO")):
            return "origen", ctx
        if any(
            p in n
            for p in ("FASE TECNICA", "PASAN", "AVANZAN", "AVANZA", "SIGUIENTE ETAPA", "RECOMENDADOS", "PRESELECCION", "ENTREVISTA")
        ):
            return "fase_tecnica", ctx
        if any(p in n for p in ("BORRADOR", "CORREO DE", "ESCRIBE UN CORREO", "REDACT", "RECHAZO", "CONVOC", "INVITACION", "EMAIL DE")):
            return "borrador", ctx
        # Si menciona nombre -> detalle de candidato. "Brechas" del mercado solo
        # si NO hay un postulante nombrado y no pregunta por "sus" brechas.
        if "BRECHA" in n:
            if menciona_nombre() or (sesion.candidato_nombre and "SUS" in n):
                return "candidato", ctx
            return "brechas", ctx
        if any(
            p in n
            for p in ("CANDIDATO", "POSTULANTE", "PERFIL", "HOJA DE VIDA", "FORTALEZAS", "FORTALEZA", "TELEFONO", "NUMERO DE", "CORREO DEL", "QUIEN ES", "SU SCORE", "SU PUNTAJE", "COMO LE FUE", "SU EMAIL")
        ):
            return "candidato", ctx
        if any(p in n for p in ("BRECHA", "BRECHAS", "MERCADO", "COMUNES", "QUE LES FALTA", "GAPS", "TENDENCI")):
            return "brechas", ctx
        if any(p in n for p in ("RANKING", "TOP", "MEJORES", "MEJOR", "PUNTAJE", "PUNTUACION", "CLASIFICACION", "ORDEN", "COMPATIBILIDAD", "CLASIFICADOS")):
            return "ranking", ctx
        if any(p in n for p in ("PIPELINE", "ESTADO", "ESTADOS", "SITUACION", "RESUMEN", "POSTULACIONES", "CANDIDATURAS RECIBIDAS", "CUANTAS", "CUANTOS", "ILEGIBLE", "PENDIENTE", "LOTE", "INGESTA", "REINTENT")):
            return "pipeline", ctx
        # Seguimiento con entidad en foco.
        if sesion.candidato_nombre and any(p in n for p in ("SU TELEFONO", "Y EL", "Y ELLA", "EL NUMERO", "EL CORREO", "QUIEN ES")):
            ctx["candidato"] = sesion.candidato_nombre
            return "candidato", ctx
        if sesion.vacante_carpeta and any(p in n for p in ("ESA VACANTE", "AHI", "DE ESA")):
            ctx["vacante"] = sesion.vacante_carpeta
            return "ranking", ctx
        return "fallback", ctx

    # ------------------------------------------------------------- despacho
    def _ejecutar(
        self, intencion: str, pregunta: str, ctx: dict[str, Any], sesion: Sesion
    ) -> dict[str, Any]:
        manejadores = {
            "saludo": self._saludo,
            "ayuda": self._ayuda,
            "reiniciar": self._reiniciar,
            "ranking": self._ranking,
            "candidato": self._candidato,
            "fase_tecnica": self._fase_tecnica,
            "pipeline": self._pipeline,
            "brechas": self._brechas,
            "comparar": self._comparar,
            "origen": self._origen,
            "borrador": self._borrador,
            "costos": self._costos,
        }
        handler = manejadores.get(intencion, self._fallback)
        try:
            return handler(pregunta, ctx, sesion)
        except Exception as exc:  # nunca debe tumbar el chat
            LOG.exception("Intencion '%s' fallo: %s", intencion, exc)
            return self._fallback(pregunta, ctx, sesion)

    # -------------------------------------------------------------- nuclei
    def _saludo(self, pregunta: str, ctx: dict[str, Any], sesion: Sesion) -> dict[str, Any]:
        return {
            "mensaje": (
                "Hola. Soy el asistente del area de talento y te respondo con "
                "los datos ya evaluados. Preguntame por el ranking, un postulante, "
                "la fase tecnica, brechas comunes, el origen de las postulaciones "
                "o los costos."
            ),
            "bloques": [],
            "sugerencias": self._sugerencias_inicio(),
        }

    def _sugerencias_inicio(self) -> list[str]:
        vacs = datos.vacantes(self._cfg)
        sugerencias = []
        for v in vacs[:2]:
            sugerencias.append(f"Ranking de {v['vacante_id']}")
        sugerencias.append("¿Quienes pasan a fase tecnica?")
        sugerencias.append("¿Cuales son las brechas mas comunes?")
        sugerencias.append("¿Cuanto hemos gastado en IA?")
        return sugerencias

    def _ayuda(self, pregunta: str, ctx: dict[str, Any], sesion: Sesion) -> dict[str, Any]:
        items = [
            "Ranking por vacante (p. ej. 'ranking de ANALISTA DE DATOS').",
            "Detalle de un postulante (p. ej. 'fortalezas y brechas de Ana Gomez').",
            "Quienes pasan a fase tecnica (clasificacion Alta).",
            "Resumen de postulaciones por estado y vacante.",
            "Brechas mas comunes entre los postulantes.",
            "Compara dos candidatos (p. ej. 'compara a Ana con Luis').",
            "Origen de las postulaciones por dominio de correo.",
            "Borrador de correo (avance / rechazo) para un candidato.",
            "Simulacion de pesos: panel 'Simulador' (recalcula el score, sin IA).",
            "Costos: panel 'Costos' o pregunta 'cuanto hemos gastado'.",
        ]
        return {
            "mensaje": "Puedo ayudarte con consultas operativas sobre los datos evaluados:",
            "bloques": [{"tipo": "lista", "titulo": "Que puedes preguntar", "items": items}],
            "sugerencias": self._sugerencias_inicio(),
        }

    def _reiniciar(self, pregunta: str, ctx: dict[str, Any], sesion: Sesion) -> dict[str, Any]:
        sesion.reiniciar()
        return {
            "mensaje": "Listo, reinicie la conversacion (sin contexto previo).",
            "bloques": [],
            "sugerencias": self._sugerencias_inicio(),
        }

    # ------------------------------------------------------------ ranking
    def _elegir_vacante(
        self, pregunta: str, ctx: dict[str, Any], sesion: Sesion
    ) -> str | None:
        carpeta_explicita = ctx.get("vacante")
        if carpeta_explicita:
            return carpeta_explicita
        n = normalizar(pregunta)
        for v in datos.vacantes(self._cfg):
            if (
                normalizar(v["vacante_id"]) in n
                or normalizar(v["carpeta"]) in n
                or normalizar(v["vacante_id"].split(" ")[0]) in n
            ):
                return v["carpeta"]
        if sesion.vacante_carpeta:
            return sesion.vacante_carpeta
        return None

    def _ranking(self, pregunta: str, ctx: dict[str, Any], sesion: Sesion) -> dict[str, Any]:
        vacs = datos.vacantes(self._cfg)
        if not vacs:
            return self._sin_datos()
        carpeta = self._elegir_vacante(pregunta, ctx, sesion)
        if carpeta is None:
            return {
                "mensaje": "Tenemos evaluaciones para varias vacantes. ¿De cual quieres el ranking?",
                "sugerencias": [f"Ranking de {v['vacante_id']}" for v in vacs],
                "bloques": [],
            }
        vacante_id, filas = datos.ranking(self._cfg, carpeta)
        sesion.limite(carpeta)
        if not filas:
            return {
                "mensaje": f"No hay postulantes evaluados para {vacante_id}.",
                "sugerencias": [f"Ranking de {v['vacante_id']}" for v in vacs],
                "bloques": [],
            }
        filas_tabla = [
            [
                _celda(f["posicion"]),
                f["nombre"],
                _celda(f["match_score"], f"score {_CLASE.get(f['clasificacion'], '')}"),
                _celda(f["clasificacion"], _CLASE.get(f["clasificacion"])),
            ]
            for f in filas
        ]
        top = next((f for f in filas if f["clasificacion"] == "Alta"), None)
        mensaje = f"Ranking de {vacante_id} ({len(filas)} evaluados)."
        if top:
            mensaje += f" El primero es {top['nombre']} con {top['match_score']}."
        elif filas:
            mensaje += " Aun no hay candidatos de compatibilidad Alta."
        return {
            "mensaje": mensaje,
            "bloques": [
                {
                    "tipo": "tabla",
                    "titulo": "Ranking por puntaje de compatibilidad",
                    "columnas": ["#", "Postulante", "Puntaje", "Nivel"],
                    "filas": filas_tabla,
                }
            ],
            "sugerencias": self._sugerencias_ranking(filas),
        }

    def _sugerencias_ranking(self, filas: list[dict[str, Any]]) -> list[str]:
        out = []
        if any(f["clasificacion"] == "Alta" for f in filas):
            out.append("¿Quienes pasan a fase tecnica?")
        if filas:
            out.append(f"Fortalezas y brechas de {filas[0]['nombre'].strip()}")
        out.append("¿Cuantas postulaciones tenemos en total?")
        return out

    # ----------------------------------------------------------- candidato
    def _encontrar_candidato(
        self, texto: str, sesion: Sesion
    ) -> dict[str, Any] | None:
        """Busca un evaluado por nombre (o token del nombre) en el mensaje.

        Si no hay coincidencia y la sesion tiene un candidato en foco, devuelve
        ese (seguimientos tipo "¿su telefono?").
        """
        n = normalizar(texto)
        docs = datos.docs_evaluados(self._cfg)
        puntuados = []
        for e in docs:
            nombre = normalizar(e["fila"]["nombre"])
            if not nombre:
                continue
            if nombre in n:
                puntuados.append((2, e))
            elif any(t in n for t in _nombre_tokens(nombre)):
                puntuados.append((1, e))
        puntuados.sort(key=lambda pe: (-pe[0], -len(pe[1]["fila"]["nombre"])))
        if not puntuados and sesion.candidato_nombre:
            for e in docs:
                if normalizar(e["fila"]["nombre"]) == normalizar(sesion.candidato_nombre):
                    return e
        return puntuados[0][1] if puntuados else None

    def _candidato(self, pregunta: str, ctx: dict[str, Any], sesion: Sesion) -> dict[str, Any]:
        nombre = ctx.get("candidato")
        e = self._encontrar_candidato(pregunta if not nombre else nombre, sesion)
        if e is None:
            nombres = [d["fila"]["nombre"].strip() for d in datos.docs_evaluados(self._cfg)]
            return {
                "mensaje": "No encontre a ese candidato. Estos son los postulantes evaluados:",
                "bloques": [{"tipo": "lista", "titulo": "Postulantes evaluados", "items": nombres}],
                "sugerencias": [f"Fortalezas de {n}" for n in nombres[:3]],
            }
        doc = e["doc"]
        fila = e["fila"]
        sesion.en_foco_candidato(fila["id_candidato"], fila["nombre"])
        sesion.limite(e["carpeta"])
        efectivo = int(doc.get("telefono") or 0) or doc.get("telefono")
        meta = [
            f"Vacante: {doc.get('vacante_id') or e['carpeta']}",
            f"Clasificacion: {fila['clasificacion']}",
            "Telefono: " + (str(efectivo) if efectivo else "sin datos"),
            "Correo: " + (doc.get("email_remitente") or "sin datos"),
        ]
        bloques = [
            {
                "tipo": "tarjetas",
                "titulo": "Puntaje de compatibilidad",
                "items": [
                    {
                        "titulo": fila["nombre"],
                        "subtitulo": f"{fila['match_score']} sobre 100",
                        "etiqueta": fila["clasificacion"],
                        "clase": _CLASE.get(fila["clasificacion"], ""),
                        "meta": meta,
                    }
                ],
            }
        ]
        if doc.get("fortalezas"):
            bloques.append(
                {"tipo": "lista", "titulo": "Fortalezas", "items": doc["fortalezas"]}
            )
        if doc.get("brechas"):
            bloques.append(
                {"tipo": "lista", "titulo": "Aspectos por reforzar", "items": doc["brechas"]}
            )
        if doc.get("requisito_esencial_ausente"):
            bloques.append(
                {
                    "tipo": "lista",
                    "titulo": "Requisito esencial ausente",
                    "items": [{"texto": r, "clase": "baja"} for r in doc["requisito_esencial_ausente"]],
                }
            )
        mensaje = (
            f"Estos son los datos de {fila['nombre'].strip()} "
            f"({fila['clasificacion']}, {fila['match_score']}/100)."
        )
        return {
            "mensaje": mensaje,
            "bloques": bloques,
            "sugerencias": [
                f"¿Su telefono?",
                f"Compara a {fila['nombre'].strip()} con otro postulante",
                "¿Quienes pasan a fase tecnica?",
            ],
        }

    # --------------------------------------------------------- fase tecnica
    def _fase_tecnica(self, pregunta: str, ctx: dict[str, Any], sesion: Sesion) -> dict[str, Any]:
        docs = datos.docs_evaluados(self._cfg)
        altos = [
            e
            for e in docs
            if (e["fila"].get("clasificacion") or "") == "Alta"
        ]
        altos.sort(key=lambda e: e["fila"]["match_score"], reverse=True)
        if not altos:
            return {
                "mensaje": (
                    "Ningun postulante evaluado tiene clasificacion Alta (>= 80). "
                    "Los de Media (50-79) requieren revision manual."
                ),
                "sugerencias": ["¿Cuantas postulaciones tenemos?", "Mostrar el ranking completo"],
                "bloques": [],
            }
        items = []
        for e in altos:
            doc = e["doc"]
            efectivo = int(doc.get("telefono") or 0) or doc.get("telefono")
            items.append(
                {
                    "titulo": e["fila"]["nombre"],
                    "subtitulo": f"{e['fila']['match_score']}/100 · {e['doc'].get('vacante_id') or e['carpeta']}",
                    "etiqueta": "Alta",
                    "clase": "alta",
                    "meta": [
                        "Telefono: " + (str(efectivo) if efectivo else "sin datos"),
                        "Correo: " + (doc.get("email_remitente") or "sin datos"),
                    ],
                }
            )
        return {
            "mensaje": (
                f"{len(altos)} postulante(s) con compatibilidad Alta pasan a "
                "fase tecnica (sugerencia de la regla de RRHH)."
            ),
            "bloques": [{"tipo": "tarjetas", "titulo": "Pasan a fase tecnica", "items": items}],
            "sugerencias": [
                "Crea un borrador de invitacion a entrevista",
                "¿Cuales son las brechas mas comunes?",
            ],
        }

    # ------------------------------------------------------------- pipeline
    def _pipeline(self, pregunta: str, ctx: dict[str, Any], sesion: Sesion) -> dict[str, Any]:
        resumen = datos.resumen_ingesta(self._cfg)
        por_estado = resumen.get("por_estado") or {}
        por_vacante = resumen.get("por_vacante") or {}
        items_estado = [
            {"texto": f"{clave}: {cant} postulaciones", "clase": "media" if "Pendiente" in clave else None}
            for clave, cant in sorted(por_estado.items(), key=lambda kv: -kv[1])
        ]
        filas_tabla = [
            [
                v,
                _celda(fila.get("total", 0)),
                _celda(fila.get("evaluados", 0), "alta"),
                _celda(fila.get("listos", 0)),
                _celda(fila.get("errores", 0), "baja"),
                _celda(fila.get("reintentos", 0), "media"),
            ]
            for v, fila in por_vacante.items()
        ]
        bloques = [
            {
                "tipo": "lista",
                "titulo": f"Resumen del lote ({resumen.get('total_silver', 0)} postulaciones en silver)",
                "items": items_estado,
            }
        ]
        if filas_tabla:
            bloques.insert(
                0,
                {
                    "tipo": "tabla",
                    "titulo": "Por vacante",
                    "columnas": ["Vacante", "Total", "Evaluados", "Pendientes", "Errores", "Reintentos"],
                    "filas": filas_tabla,
                },
            )
        return {
            "mensaje": "Asi esta la pipeline de postulaciones:",
            "bloques": bloques,
            "sugerencias": ["¿Quienes pasan a fase tecnica?", "¿Cuales son las brechas mas comunes?"],
        }

    # -------------------------------------------------------------- brechas
    def _brechas(self, pregunta: str, ctx: dict[str, Any], sesion: Sesion) -> dict[str, Any]:
        docs = datos.docs_evaluados(self._cfg)
        conteo: dict[str, int] = {}
        con_requisito_ausente = 0
        for e in docs:
            for b in e["doc"].get("brechas") or []:
                clave = b.strip()
                if clave:
                    conteo[clave] = conteo.get(clave, 0) + 1
            if e["doc"].get("requisito_esencial_ausente"):
                con_requisito_ausente += 1
        if not docs:
            return self._sin_datos()
        n = len(docs)
        top = sorted(conteo.items(), key=lambda kv: -kv[1])[:8]
        items = [
            {"texto": f"{b} ({c} de {n})", "clase": "media" if c > 1 else None}
            for b, c in top
        ]
        mensaje = (
            f"Analice {n} postulantes evaluados. Estas son las brechas mas "
            "frecuentes y pueden ayudarte a ajustar los requisitos de la vacante:"
        )
        if con_requisito_ausente:
            mensaje += (
                f" Ademas, {con_requisito_ausente} no cumplen un requisito "
                "esencial (puntaje 0 en ese bloque)."
            )
        return {
            "mensaje": mensaje,
            "bloques": [{"tipo": "lista", "titulo": "Brechas mas comunes", "items": items}],
            "sugerencias": ["¿De donde vienen los postulantes?", "¿Cuantas postulaciones tenemos?"],
        }

    # ------------------------------------------------------------- comparar
    def _comparar(self, pregunta: str, ctx: dict[str, Any], sesion: Sesion) -> dict[str, Any]:
        docs = datos.docs_evaluados(self._cfg)
        elegidos = self._extraer_dos_candidatos(pregunta, docs)
        if len(elegidos) < 2:
            return {
                "mensaje": "Necesito dos postulantes para comparar. Menciona sus nombres, p. ej. 'compara a Ana con Luis'.",
                "sugerencias": [f"Compara a {d['fila']['nombre'].strip()} con otro" for d in docs[:2]],
                "bloques": [],
            }
        e1, e2 = elegidos
        filas = self._filas_comparativa(e1, e2)
        s1, s2 = e1["fila"]["match_score"], e2["fila"]["match_score"]
        mensaje = (
            f"Comparativa entre {e1['fila']['nombre'].strip()} ({s1}) y "
            f"{e2['fila']['nombre'].strip()} ({s2})."
        )
        return {
            "mensaje": mensaje,
            "bloques": [
                {
                    "tipo": "tabla",
                    "titulo": "Comparacion lado a lado",
                    "columnas": ["Criterio", e1["fila"]["nombre"].strip(), e2["fila"]["nombre"].strip()],
                    "filas": filas,
                }
            ],
            "sugerencias": [
                f"Fortalezas y brechas de {e1['fila']['nombre'].strip()}",
                "¿Quienes pasan a fase tecnica?",
            ],
        }

    def _extraer_dos_candidatos(
        self, pregunta: str, docs: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        n = normalizar(pregunta)
        puntuados = []
        for e in docs:
            nombre = normalizar(e["fila"]["nombre"])
            if not nombre:
                continue
            if nombre in n:
                puntuados.append((2, e))
            elif any(t in n for t in _nombre_tokens(nombre)):
                puntuados.append((1, e))
        puntuados.sort(key=lambda pe: (-pe[0], -len(pe[1]["fila"]["nombre"])))
        elegidos: list[dict[str, Any]] = []
        for _, e in puntuados:
            if e not in elegidos:
                elegidos.append(e)
            if len(elegidos) == 2:
                break
        return elegidos

    def _filas_comparativa(self, e1: dict[str, Any], e2: dict[str, Any]) -> list[list[Any]]:
        def bloque(doc: dict[str, Any], bloque_nombre: str) -> Any:
            des = doc.get("desglose") or {}
            return ((des.get(bloque_nombre) or {}).get("parcial", 0))

        habilidades1 = ", ".join(datos.habilidades(e1["doc"]))
        habilidades2 = ", ".join(datos.habilidades(e2["doc"]))
        celdas = [
            ("Puntaje de compatibilidad", e1["fila"]["match_score"], e2["fila"]["match_score"]),
            ("Nivel", e1["fila"]["clasificacion"], e2["fila"]["clasificacion"]),
            ("Habilidades (bloque 50%)", bloque(e1["doc"], "habilidades"), bloque(e2["doc"], "habilidades")),
            ("Experiencia (bloque 30%)", bloque(e1["doc"], "experiencia"), bloque(e2["doc"], "experiencia")),
            ("Formacion (bloque 20%)", bloque(e1["doc"], "formacion"), bloque(e2["doc"], "formacion")),
            ("Anos de experiencia", datos.experiencia_anos(e1["doc"]), datos.experiencia_anos(e2["doc"])),
            ("Formaciones", "; ".join(datos.formaciones(e1["doc"])[:2]), "; ".join(datos.formaciones(e2["doc"])[:2])),
            ("Habilidades", habilidades1, habilidades2),
        ]
        filas = []
        for criterio, a, b in celdas:
            filas.append([criterio, _celda(a), _celda(b)])
        return filas

    # --------------------------------------------------------------- origen
    def _origen(self, pregunta: str, ctx: dict[str, Any], sesion: Sesion) -> dict[str, Any]:
        docs = datos.docs_evaluados(self._cfg)
        if not docs:
            return self._sin_datos()
        por_dominio: dict[str, dict[str, Any]] = {}
        for e in docs:
            d = datos.dominio(e["doc"]) or "desconocido"
            fila = por_dominio.setdefault(d, {"total": 0, "nombres": [], "puntajes": [], "clases": []})
            fila["total"] += 1
            fila["nombres"].append(e["fila"]["nombre"])
            fila["puntajes"].append(float(e["fila"]["match_score"] or 0))
            fila["clases"].append(e["fila"].get("clasificacion", ""))
        filas = []
        for d, f in sorted(por_dominio.items(), key=lambda kv: -kv[1]["total"]):
            prom = round(sum(f["puntajes"]) / len(f["puntajes"]), 1)
            mejor = f["nombres"][f["puntajes"].index(max(f["puntajes"]))].strip()
            filas.append(
                [
                    d or "desconocido",
                    _celda(f["total"]),
                    _celda(prom, "alta" if prom >= 80 else "media" if prom >= 50 else "baja"),
                    mejor,
                ]
            )
        return {
            "mensaje": "Distribucion de postulantes evaluados por dominio del correo:",
            "bloques": [
                {
                    "tipo": "tabla",
                    "titulo": "Origen (dominio)",
                    "columnas": ["Dominio", "Candidatos", "Puntaje prom.", "Mejor postulante"],
                    "filas": filas,
                }
            ],
            "sugerencias": ["¿Cuales son las brechas mas comunes?", "¿Quienes pasan a fase tecnica?"],
        }

    # ------------------------------------------------------------- borrador
    def _borrador(self, pregunta: str, ctx: dict[str, Any], sesion: Sesion) -> dict[str, Any]:
        e = self._encontrar_candidato(pregunta, sesion)
        if e is None:
            nombres = [d["fila"]["nombre"].strip() for d in datos.docs_evaluados(self._cfg)]
            return {
                "mensaje": "Para redactar un borrador dime para quien:",
                "sugerencias": [f"Correo de avance para {n}" for n in nombres[:3]],
                "bloques": [],
            }
        fila = e["fila"]
        doc = e["doc"]
        sesion.en_foco_candidato(fila["id_candidato"], fila["nombre"])
        sesion.limite(e["carpeta"])
        nombre = fila["nombre"].strip()
        clasif = fila.get("clasificacion", "")
        titulo = "Borrador de correo"
        if clasif == "Alta":
            cuerpo = (
                f"Asunto: Invitacion a fase tecnica\n\nHola {nombre},\n\n"
                f"Felicitaciones, tu perfil califico con compatibilidad alta para "
                f"{doc.get('vacante_id') or e['carpeta']}. Te invitamos a una "
                "prueba/entrevista tecnica. Te contactaremos por este medio para "
                "coordinar la fecha."
            )
        elif clasif == "Media":
            cuerpo = (
                f"Asunto: Avance en el proceso\n\nHola {nombre},\n\n"
                f"Tu postulacion para {doc.get('vacante_id') or e['carpeta']} "
                "avanza a una revision de perfil. Queremos conocerte mejor y "
                "programaremos una breve entrevista para complementar tu evaluacion."
            )
        else:
            cuerpo = (
                f"Asunto: Postulacion recibida\n\nHola {nombre},\n\n"
                "Gracias por postular a nuestra vacante. Hemos recibido muchas "
                "candidaturas de excelente nivel y, tras evaluarlas, decidimos no "
                "continuar con tu perfil en esta ocasion. Te invitamos a seguir "
                "aplicando en futuras convocatorias. Mucho exito."
            )
        return {
            "mensaje": f"Borrador listo para {nombre} ({clasif or 'sin clasificar'}).",
            "bloques": [
                {"tipo": "lista", "titulo": "Borrador de correo", "items": cuerpo.splitlines()}
            ],
            "sugerencias": [
                f"Fortalezas y brechas de {nombre}",
                "¿Quienes pasan a fase tecnica?",
            ],
        }

    # --------------------------------------------------------------- costos
    def _costos(self, pregunta: str, ctx: dict[str, Any], sesion: Sesion) -> dict[str, Any]:
        f2 = datos.tokens_f2(self._cfg)
        usos_chat = costo_mod.leer_usos(
            Path(self._cfg.gold_dir) / "costo" / "uso_chat.jsonl"
        )
        resumen_chat = costo_mod.resumir(usos_chat)
        offline = not (self._cfg.proveedor_chat or "").strip()
        messages = [
            f"Fase 2 (evaluacion): {f2['candidatos']} candidatos evaluados, "
            f"{f2['total_tokens']} tokens en total.",
        ]
        if usos_chat:
            messages.append(
                f"Chat: {resumen_chat['llamadas']} llamada(s), "
                f"{resumen_chat['total_tokens']} tokens, "
                f"~$ {resumen_chat['costo_usd']:.6f} estimado."
            )
        else:
            messages.append(
                "Chat: sin llamadas a IA hasta ahora (modo offline) - "
                "costo $0."
            )
        items = [
            {
                "texto": (
                    "Todos los bloques visuales (tablas, tarjetas, simulaciones) "
                    "se generan en codigo, sin gastar tokens."
                ),
                "clase": "alta",
            }
        ]
        if offline:
            items.insert(
                0,
                {"texto": "PROVEEDOR_CHAT esta vacio: el chat funciona sin IA (0 tokens, $0).", "clase": "alta"},
            )
        return {
            "mensaje": "Resumen de uso de la IA en el proyecto:",
            "bloques": [
                {"tipo": "lista", "titulo": "Uso y costos", "items": messages},
                {"tipo": "lista", "titulo": "Costo zero garantizado", "items": items},
            ],
            "sugerencias": ["¿Quienes pasan a fase tecnica?", "¿Cuantas postulaciones tenemos?"],
        }

    # ------------------------------------------------------------- fallback
    def _sin_datos(self) -> dict[str, Any]:
        return {
            "mensaje": (
                "Aun no hay candidatos evaluados (gold vacio). Corre primero la "
                "ingesta (F1) y la evaluacion (F2)."
            ),
            "sugerencias": ["Ayuda"],
            "bloques": [],
        }

    def _fallback(self, pregunta: str, ctx: dict[str, Any], sesion: Sesion) -> dict[str, Any]:
        return {
            "mensaje": (
                "Lo siento, no entendi la consulta. Te sugiero algunas de estas "
                "preguntas para empezar:"
            ),
            "bloques": [],
            "sugerencias": self._sugerencias_inicio() + ["Ayuda"],
        }

    # ---------------------------------------------- IA opcional (0 default)
    def _aplicar_ia_opcional(
        self, sesion: Sesion, pregunta: str, respuesta: dict[str, Any]
    ) -> None:
        proveedor = (self._cfg.proveedor_chat or "").strip().lower()
        if proveedor in ("", "ninguno", "none", "offline"):
            respuesta["uso"] = None
            respuesta["modo"] = "offline"
            return
        api_key = self._cfg.groq_api_key if proveedor == "groq" else ""
        if not api_key:
            respuesta["uso"] = None
            respuesta["modo"] = "offline"
            return
        if not sesion.usar_ia():
            respuesta["uso"] = None
            respuesta["modo"] = "offline"
            respuesta["aviso_ia"] = {
                "mensaje": (
                    "Modo demo: agotaste las consultas con IA de esta conversación. "
                    "El motor sigue respondiendo con los datos verificados ($0)."
                ),
            }
            return
        try:
            contexto = json.dumps(
                {
                    "mensaje_interes": pregunta,
                    "entidad_en_foco": sesion.resumen(),
                    "datos_verificados": respuesta.get("bloques") or [],
                },
                ensure_ascii=False,
                default=str,
            )
            try:
                prompt = cargar_prompt(
                    str(_RUTA_PROMPT_CHAT),
                    {
                        "pregunta": pregunta,
                        "contexto_datos": contexto,
                        "entidad_en_foco": json.dumps(sesion.resumen(), ensure_ascii=False),
                    },
                )
            except Exception:
                prompt = (
                    "Respuesta tuya sobre los datos dados, en espanol, breve y "
                    "sin inventar datos.\nContexto: " + contexto +
                    "\nPregunta: " + pregunta
                )
            from ..core.llm import generar_texto

            texto, uso = generar_texto(
                proveedor,
                self._cfg.modelo_chat,
                api_key,
                prompt,
                temperature=0.4,
                formato_json=False,
            )
            registro = costo_mod.registrar_uso(
                str(Path(self._cfg.gold_dir) / "costo" / "uso_chat.jsonl"),
                "chat",
                proveedor,
                self._cfg.modelo_chat,
                uso["prompt"],
                uso["completado"],
                self._cfg.tarifas_costo,
                pregunta=pregunta[:120],
            )
            respuesta["mensaje"] = texto.strip() or respuesta["mensaje"]
            respuesta["modo"] = proveedor
            respuesta["uso"] = {
                "proveedor": proveedor,
                "modelo": self._cfg.modelo_chat,
                "tokens": uso,
                "costo_usd": registro["costo_usd"],
            }
        except ErrorModelo as exc:
            LOG.warning("IA del chat no disponible (%s); se responde offline.", exc)
            respuesta["modo"] = "offline"
            respuesta["uso"] = None
            respuesta["aviso_ia"] = {
                "mensaje": "La IA opcional no respondio; te contesto con los datos verificados.",
            }