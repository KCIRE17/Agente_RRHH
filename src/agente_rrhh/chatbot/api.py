"""API web del chatbot F4 (FastAPI + frontend estatico).

Solo escucha en ``127.0.0.1`` (datos personales en local). El motor responde
100% en codigo; la IA es opcional y se controla con ``PROVEEDOR_CHAT`` del
.env (vacio = offline, costo $0).
"""

from __future__ import annotations

import secrets
import time
from pathlib import Path
from typing import Any

from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from ..core import costo as costo_mod
from ..core.config import PROVEEDOR_CHAT_OFFLINE, Config
from ..evaluation.reglas import PESOS, UMBRAL_ALTA, UMBRAL_MEDIA
from . import datos, preguntas_generales, sesion as sesion_mod, simulador
from .motor import MotorChat

_FRONTEND = Path(__file__).resolve().parent / "frontend"

# Vida útil de los tokens de sesión del login F4.
_TOKEN_TTL_SEG = 12 * 3600


# -------------------------------------------------------------- modelos pyd
class MensajeChat(BaseModel):
    mensaje: str = Field(min_length=1, max_length=500)
    sesion_id: str = ""


class Credenciales(BaseModel):
    usuario: str = Field(min_length=1, max_length=64)
    clave: str = Field(min_length=1, max_length=128)


class PesosSimulacion(BaseModel):
    habilidades: float = 50
    experiencia: float = 30
    formacion: float = 20
    vacante: str = ""


# --------------------------------------------------------------- factories
def crear_app(cfg: Config | None = None) -> FastAPI:
    app = FastAPI(title="Agente RRHH - Chatbot F4", version="0.1.0")
    conf = cfg or Config.desde_env()
    limite_ia = (
        conf.consultas_ia_demo if (conf.proveedor_chat or "").strip() else None
    )
    dir_persist = (
        str(Path(conf.gold_dir) / "chat_sesiones") if conf.chat_persistencia else None
    )
    estado: dict[str, Any] = {
        "cfg": conf,
        "motor": None,
        "sesiones": sesion_mod.AlmacenSesiones(
            limite_ia=limite_ia, dir_persistencia=dir_persist
        ),
        "tokens": {},
    }
    estado["motor"] = MotorChat(estado["cfg"])

    def _motor() -> MotorChat:
        return estado["motor"]

    # -------------------------------------------------------------- login
    def _emitir_token() -> str:
        token = secrets.token_urlsafe(32)
        estado["tokens"][token] = time.time()
        return token

    def _token_valido(token: str | None) -> bool:
        if not token:
            return False
        emitido = estado["tokens"].get(token)
        if emitido is None:
            return False
        if time.time() - emitido > _TOKEN_TTL_SEG:
            estado["tokens"].pop(token, None)
            return False
        return True

    def _extraer_token(authorization: str | None) -> str:
        if authorization and authorization.startswith("Bearer "):
            return authorization[7:]
        return ""

    # Dependencia de auth para los endpoints de datos. Con login desactivado
    # (sin credenciales en .env) el acceso queda abierto, con aviso visible.
    def _requiere_login(
        authorization: str | None = Header(default=None),
    ) -> None:
        if not estado["cfg"].login_habilitado:
            return
        if not _token_valido(_extraer_token(authorization)):
            raise HTTPException(
                status_code=401, detail="No autorizado: inicia sesión para continuar."
            )

    @app.get("/api/health")
    def health() -> dict[str, Any]:
        cfg = estado["cfg"]
        return {
            "ok": True,
            "modo": (
                "offline" if not (cfg.proveedor_chat or "").strip() else cfg.proveedor_chat
            ),
            "data_dir": cfg.data_dir,
            "proveedor_chat": cfg.proveedor_chat or PROVEEDOR_CHAT_OFFLINE,
            "modelo_chat": cfg.modelo_chat,
            "limite_ia_demo": limite_ia,
            "login": "habilitado" if cfg.login_habilitado else "desactivado",
        }

    @app.post("/api/login")
    def login(body: Credenciales) -> dict[str, Any]:
        cfg = estado["cfg"]
        if not cfg.login_habilitado:
            raise HTTPException(
                status_code=503,
                detail="Login desactivado: configura ADMIN_USUARIO y ADMIN_CLAVE en .env.",
            )
        if not cfg.verificar(body.usuario, body.clave):
            raise HTTPException(status_code=401, detail="Usuario o contraseña incorrectos.")
        return {
            "token": _emitir_token(),
            "usuario": cfg.admin_usuario,
            "expira_horas": int(_TOKEN_TTL_SEG // 3600),
        }

    @app.post("/api/logout")
    def logout(authorization: str | None = Header(default=None)) -> dict[str, Any]:
        estado["tokens"].pop(_extraer_token(authorization), None)
        return {"ok": True}

    @app.get("/api/me")
    def me(authorization: str | None = Header(default=None)) -> dict[str, Any]:
        cfg = estado["cfg"]
        if not cfg.login_habilitado:
            return {"autenticado": False, "login_habilitado": False}
        return {
            "autenticado": _token_valido(_extraer_token(authorization)),
            "login_habilitado": True,
            "usuario": cfg.admin_usuario,
            "expira_horas": int(_TOKEN_TTL_SEG // 3600),
        }

    @app.get("/api/config", dependencies=[Depends(_requiere_login)])
    def config_publica() -> dict[str, Any]:
        cfg = estado["cfg"]
        return {
            "offline": not (cfg.proveedor_chat or "").strip(),
            "proveedor_chat": cfg.proveedor_chat or "ninguno",
            "modelo_chat": cfg.modelo_chat,
            "tarifas": costo_mod.leer_tarifas(cfg.tarifas_costo),
            "limite_ia_demo": limite_ia,
            "persistencia_chat": estado["sesiones"].persistencia,
        }

    @app.post("/api/chat", dependencies=[Depends(_requiere_login)])
    def chat(body: MensajeChat) -> dict[str, Any]:
        cfg = estado["cfg"]
        sesion_id = body.sesion_id or estado["sesiones"].nueva()
        sesion = estado["sesiones"].obtener(sesion_id)
        respuesta = _motor().resolver(body.mensaje, sesion)
        if respuesta.get("intencion") == "fallback":
            respuesta["aviso"] = (
                "No reconoci tu consulta exacta, pero te dejo opciones o una "
                "respuesta general:"
            )
            faq = preguntas_generales.buscar(body.mensaje)
            if faq:
                respuesta["faq"] = faq
        respuesta["sesion_id"] = sesion_id
        sesion.agregar_historial("usuario", body.mensaje)
        sesion.agregar_historial(
            "asistente",
            respuesta.get("mensaje", ""),
            intencion=respuesta.get("intencion"),
            modo=respuesta.get("modo"),
        )
        estado["sesiones"].guardar(sesion)
        return respuesta

    @app.get(
        "/api/sesiones/{sesion_id}/historial",
        dependencies=[Depends(_requiere_login)],
    )
    def historial(sesion_id: str) -> dict[str, Any]:
        sesion = estado["sesiones"].obtener(sesion_id)
        return {
            "sesion_id": sesion_id,
            "historial": sesion.historial,
            "resumen": sesion.resumen(),
            "persistencia": estado["sesiones"].persistencia,
        }

    @app.get("/api/vacantes", dependencies=[Depends(_requiere_login)])
    def vacantes() -> dict[str, Any]:
        return {"vacantes": datos.vacantes(estado["cfg"])}

    @app.get("/api/ranking", dependencies=[Depends(_requiere_login)])
    def ranking(carpeta: str = "") -> dict[str, Any]:
        cfg = estado["cfg"]
        vacs = datos.vacantes(cfg)
        if not vacs:
            return {"carpeta": carpeta, "vacante_id": "", "candidatos": []}
        if not carpeta:
            carpeta = vacs[0]["carpeta"]
        if carpeta not in {v["carpeta"] for v in vacs}:
            raise HTTPException(status_code=404, detail="Vacante no encontrada")
        vacante_id, filas = datos.ranking(cfg, carpeta)
        return {"carpeta": carpeta, "vacante_id": vacante_id, "candidatos": filas}

    @app.get("/api/traza", dependencies=[Depends(_requiere_login)])
    def traza(carpeta: str = "", id_candidato: str = "") -> dict[str, Any]:
        """Traza auditable silver -> gold -> ranking para un candidato (E9)."""
        cfg = estado["cfg"]
        vacs = datos.vacantes(cfg)
        if not vacs:
            raise HTTPException(status_code=404, detail="No hay vacantes evaluadas.")
        carpetas = {v["carpeta"] for v in vacs}
        if not carpeta:
            carpeta = vacs[0]["carpeta"]
        if carpeta not in carpetas:
            raise HTTPException(status_code=404, detail="Vacante no encontrada.")
        vacante_id, filas = datos.ranking(cfg, carpeta)
        if not filas:
            raise HTTPException(status_code=404, detail="Ranking vacio.")
        if not id_candidato:
            id_candidato = filas[0]["id_candidato"]
        doc = datos.detalle(cfg, carpeta, id_candidato)
        if doc is None:
            raise HTTPException(status_code=404, detail="Candidato no encontrado.")
        silver = doc.get("silver") or {}
        fila = next((f for f in filas if f["id_candidato"] == id_candidato), None)
        pasos = [
            {
                "fase": "F1",
                "nombre": "Ingesta y extraccion",
                "estado": silver.get("estado_procesamiento"),
                "mensaje_id": silver.get("mensaje_id"),
                "formato_origen": silver.get("formato_origen"),
                "fecha_ingesta": silver.get("fecha_ingesta"),
                "fuente": (
                    f"data/silver/candidatos/{silver.get('id_candidato', '')}.json"
                ),
            },
            {
                "fase": "F2",
                "nombre": "Evaluacion (Match Score)",
                "match_score": doc.get("match_score"),
                "clasificacion": doc.get("clasificacion"),
                "desglose": doc.get("desglose"),
                "proveedor": doc.get("proveedor"),
                "modelo": doc.get("modelo"),
                "uso_tokens": doc.get("uso_tokens"),
                "fecha_evaluacion": doc.get("fecha_evaluacion"),
                "fuente": f"data/gold/evaluacion/{carpeta}/{id_candidato}.json",
            },
            {
                "fase": "F2",
                "nombre": "Ranking",
                "posicion": fila.get("posicion") if fila else None,
                "total_candidatos": len(filas),
                "vacante_id": vacante_id,
                "fuente": f"data/gold/evaluacion/{carpeta}/ranking.json",
            },
            {
                "fase": "F4",
                "nombre": "Consulta (chatbot)",
                "endpoint": "POST /api/chat",
                "nota": (
                    "El motor responde con estos datos verificados; la IA es "
                    "opcional (PROVEEDOR_CHAT). En offline el costo es $0."
                ),
            },
        ]
        return {
            "vacante_id": vacante_id,
            "carpeta": carpeta,
            "id_candidato": id_candidato,
            "nombre": doc.get("nombre_completo"),
            "pasos": pasos,
            "reglas": {
                "pesos": PESOS,
                "umbral_alta": UMBRAL_ALTA,
                "umbral_media": UMBRAL_MEDIA,
            },
        }

    @app.get("/api/brechas", dependencies=[Depends(_requiere_login)])
    def brechas() -> dict[str, Any]:
        cfg = estado["cfg"]
        docs = datos.docs_evaluados(cfg)
        conteo: dict[str, int] = {}
        con_ausente = 0
        for e in docs:
            for b in e["doc"].get("brechas") or []:
                if b.strip():
                    conteo[b.strip()] = conteo.get(b.strip(), 0) + 1
            if e["doc"].get("requisito_esencial_ausente"):
                con_ausente += 1
        top = sorted(conteo.items(), key=lambda kv: -kv[1])[:8]
        return {
            "total_candidatos": len(docs),
            "con_requisito_esencial_ausente": con_ausente,
            "brechas": [{"descripcion": b, "candidatos": c} for b, c in top],
        }

    @app.post("/api/simular", dependencies=[Depends(_requiere_login)])
    def simular(body: PesosSimulacion) -> dict[str, Any]:
        pesos = {
            "habilidades": body.habilidades,
            "experiencia": body.experiencia,
            "formacion": body.formacion,
        }
        resultado = simulador.simular(
            estado["cfg"], carpeta=body.vacante or None, pesos=pesos
        )
        return resultado

    @app.get("/api/costos", dependencies=[Depends(_requiere_login)])
    def costos() -> dict[str, Any]:
        cfg = estado["cfg"]
        f2 = datos.tokens_f2(cfg)
        usos = costo_mod.leer_usos(
            str(Path(cfg.gold_dir) / "costo" / "uso_chat.jsonl")
        )
        chat = costo_mod.resumir(usos)
        lotes_f2 = costo_mod.leer_usos(
            str(Path(cfg.gold_dir) / "costo" / "uso_fase2.jsonl")
        )
        return {
            "fase2": f2,
            "chat": chat,
            "fase2_lotes": lotes_f2[-10:],
            "detalle_chat": usos[-10:],
            "total_tokens": f2["total_tokens"] + chat["total_tokens"],
            "costo_total_usd": round(chat["costo_usd"], 8),
            "tarifas": costo_mod.leer_tarifas(cfg.tarifas_costo),
            "offline": not (cfg.proveedor_chat or "").strip(),
        }

    @app.get("/api/faq", dependencies=[Depends(_requiere_login)])
    def faq() -> dict[str, Any]:
        return {"preguntas": preguntas_generales.todas()}

    @app.post("/api/sesiones/nueva", dependencies=[Depends(_requiere_login)])
    def nueva_sesion() -> dict[str, str]:
        return {"sesion_id": estado["sesiones"].nueva()}

    # --------------------------------------------------------- frontend SPA
    app.mount(
        "/static",
        StaticFiles(directory=str(_FRONTEND)),
        name="static",
    )

    @app.get("/", include_in_schema=False)
    def raiz() -> FileResponse:
        return FileResponse(_FRONTEND / "index.html")

    @app.exception_handler(Exception)
    def error_inesperado(_, exc: Exception) -> JSONResponse:
        import logging

        logging.getLogger("agente_rrhh").exception("Error en API F4: %s", exc)
        return JSONResponse(status_code=500, content={"detalle": "Error interno."})

    return app