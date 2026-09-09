"""API web del chatbot F4 (FastAPI + frontend estatico).

Solo escucha en ``127.0.0.1`` (datos personales en local). El motor responde
100% en codigo; la IA es opcional y se controla con ``PROVEEDOR_CHAT`` del
.env (vacio = offline, costo $0).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from ..core import costo as costo_mod
from ..core.config import PROVEEDOR_CHAT_OFFLINE, Config
from . import datos, preguntas_generales, sesion as sesion_mod, simulador
from .motor import MotorChat

_FRONTEND = Path(__file__).resolve().parent / "frontend"


# -------------------------------------------------------------- modelos pyd
class MensajeChat(BaseModel):
    mensaje: str = Field(min_length=1, max_length=500)
    sesion_id: str = ""


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
    estado: dict[str, Any] = {
        "cfg": conf,
        "motor": None,
        "sesiones": sesion_mod.AlmacenSesiones(limite_ia=limite_ia),
    }
    estado["motor"] = MotorChat(estado["cfg"])

    def _motor() -> MotorChat:
        return estado["motor"]

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
        }

    @app.get("/api/config")
    def config_publica() -> dict[str, Any]:
        cfg = estado["cfg"]
        return {
            "offline": not (cfg.proveedor_chat or "").strip(),
            "proveedor_chat": cfg.proveedor_chat or "ninguno",
            "modelo_chat": cfg.modelo_chat,
            "tarifas": costo_mod.leer_tarifas(cfg.tarifas_costo),
            "limite_ia_demo": limite_ia,
        }

    @app.post("/api/chat")
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
        return respuesta

    @app.get("/api/vacantes")
    def vacantes() -> dict[str, Any]:
        return {"vacantes": datos.vacantes(estado["cfg"])}

    @app.get("/api/ranking")
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

    @app.get("/api/brechas")
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

    @app.post("/api/simular")
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

    @app.get("/api/costos")
    def costos() -> dict[str, Any]:
        cfg = estado["cfg"]
        f2 = datos.tokens_f2(cfg)
        usos = costo_mod.leer_usos(
            str(Path(cfg.gold_dir) / "costo" / "uso_chat.jsonl")
        )
        chat = costo_mod.resumir(usos)
        return {
            "fase2": f2,
            "chat": chat,
            "detalle_chat": usos[-10:],
            "total_tokens": f2["total_tokens"] + chat["total_tokens"],
            "costo_total_usd": round(chat["costo_usd"], 8),
            "tarifas": costo_mod.leer_tarifas(cfg.tarifas_costo),
            "offline": not (cfg.proveedor_chat or "").strip(),
        }

    @app.get("/api/faq")
    def faq() -> dict[str, Any]:
        return {"preguntas": preguntas_generales.todas()}

    @app.post("/api/sesiones/nueva")
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