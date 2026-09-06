"""Orquestación del lote de ingesta: IMAP -> extracción -> IA -> silver JSON."""

from __future__ import annotations

import json
import logging
from collections import Counter
from datetime import date, datetime, timezone
from uuid import uuid4
from typing import Any

from .agent_extractor import AgenteExtractor, ErrorAgenteExtractor
from .extractor import (
    ArchivoIlegibleError,
    ErrorExtraccion,
    FormatoNoPermitidoError,
    extraer_adjunto,
    formato_origen,
)
from .imap_client import ImapClient, Postulacion
from ..core.config import (
    ESTADO_FORMATO,
    ESTADO_ILEGIBLE,
    ESTADO_LISTO,
    ESTADO_REINTENTO,
    Config,
)
from ..core.raw_store import RawStore
from ..core.sanitizer import sanitizar
from ..core.json_store import JsonStore

LOG = logging.getLogger("agente_rrhh")


class PipelineIngesta:
    def __init__(
        self,
        cfg: Config,
        dry_run: bool = False,
        max_mensajes: int | None = None,
    ) -> None:
        self._cfg = cfg
        self._dry_run = dry_run
        self._max = max_mensajes
        self._agente = AgenteExtractor(
            cfg.gemini_api_key, cfg.modelo_gemini, cfg.prompt_extractor
        )
        self._raw = RawStore(cfg.bronze_dir)
        self._bd: JsonStore | None = JsonStore(cfg.silver_dir) if not dry_run else None

    # ------------------------------------------------------------------ flujo
    def ejecutar(self, imap: ImapClient) -> dict[str, Any]:
        """Reintentos pendientes primero y luego la ingesta de correos nuevos."""
        resumen: Counter[str] = Counter()
        detalle: list[dict[str, Any]] = []

        if not self._dry_run:
            resumen.update(self.reintentar_pendientes(detalle))

        postulaciones = imap.listar_postulaciones()
        if self._max is not None:
            postulaciones = postulaciones[: self._max]
        LOG.info("Correos con asunto '%s...': %d", self._cfg.asunto, len(postulaciones))

        for post in postulaciones:
            if self._bd is not None and self._bd.existe_mensaje(post.mensaje_id):
                LOG.info("Omitido (ya procesado, Message-ID duplicado): %s", post.asunto)
                imap.marcar_leido(post.numero)
                resumen["Omitido (duplicado)"] += 1
                continue

            documento = self._procesar_postulacion(post)
            if documento is None:
                continue

            detalle.append(
                {
                    "asunto": post.asunto,
                    "vacante": post.vacante_id,
                    "remitente": post.remitente,
                    "estado": documento["estado_procesamiento"],
                    "motivo": documento.get("motivo"),
                }
            )

            if self._dry_run:
                LOG.info("[DRY-RUN] %s -> %s", post.asunto, documento["estado_procesamiento"])
                LOG.info(
                    "JSON generado:\n%s",
                    json.dumps(documento["datos_json"], ensure_ascii=False, indent=2),
                )
            else:
                guardado = self._bd.guardar_candidato(documento)  # type: ignore[union-attr]
                imap.marcar_leido(post.numero)
                LOG.info(
                    "Guardado %s: %s (%s)",
                    "OK" if guardado else "(duplicado por race)",
                    post.asunto,
                    documento["estado_procesamiento"],
                )

            resumen[documento["estado_procesamiento"]] += 1

        LOG.info("Total de correos procesados en este lote: %d", len(postulaciones))
        LOG.info("Resumen del lote: %s", dict(resumen))
        return {"resumen": dict(resumen), "detalle": detalle, "total": len(postulaciones)}

    # ------------------------------------------------------------- candidato
    def _procesar_postulacion(self, post: Postulacion) -> dict[str, Any] | None:
        texto = None
        origen = None
        estado = None
        motivo = None
        adjunto_usado: tuple[str, bytes] | None = None

        for nombre, contenido in post.adjuntos:
            try:
                texto = extraer_adjunto(nombre, contenido)
                origen = formato_origen(nombre)
                estado = ESTADO_LISTO
                adjunto_usado = (nombre, contenido)
                break
            except FormatoNoPermitidoError as exc:
                estado, motivo, origen = ESTADO_FORMATO, str(exc), "DESCONOCIDO"
                LOG.warning("Adjunto no permitido en %s: %s", post.asunto, exc)
            except ArchivoIlegibleError as exc:
                estado, motivo, origen = ESTADO_ILEGIBLE, str(exc), "DESCONOCIDO"
                LOG.warning("Adjunto ilegible en %s: %s", post.asunto, exc)
            except ErrorExtraccion as exc:
                estado, motivo, origen = ESTADO_ILEGIBLE, str(exc), "DESCONOCIDO"
                LOG.warning("Error de extraccion en %s: %s", post.asunto, exc)

        if texto is None and estado is None and post.cuerpo.strip():
            texto = post.cuerpo
            origen = "CORREO"
            estado = ESTADO_LISTO
            motivo = None

        if texto is None and estado is None:
            estado = ESTADO_ILEGIBLE
            motivo = "Postulacion sin adjunto legible ni contenido en el cuerpo del correo."

        ruta_raw = self._guardar_archivo_original(post, adjunto_usado)

        LOG.info(
            "Remitente %s <%s> (%s) | fecha_envio=%s | x_mailer=%s",
            post.remitente_nombre or "-",
            post.remitente_email or "-",
            post.remitente_dominio or "-",
            post.fecha_envio.isoformat() if post.fecha_envio else "-",
            post.x_mailer or "-",
        )

        texto_limpio = sanitizar(texto) if texto else ""
        LOG.info("Sanetizado %s (%s): %d caracteres",
                 post.asunto, origen, len(texto_limpio))

        datos_json = None
        if estado == ESTADO_LISTO:
            try:
                datos_json = self._agente.extraer(texto_limpio, dry_run=self._dry_run)
            except ErrorAgenteExtractor as exc:
                if self._dry_run:
                    raise
                estado = ESTADO_REINTENTO
                motivo = str(exc)
                LOG.warning("Fallo Gemini para %s; queda para reintento.", post.asunto)

        return self._construir_documento(
            post, origen, texto_limpio, estado, datos_json, motivo, ruta_raw
        )

    def _guardar_archivo_original(
        self, post: Postulacion, adjunto: tuple[str, bytes] | None
    ) -> str | None:
        """Copia a data/bronze/<fecha>/<vacante>/ el adjunto usado o el cuerpo."""
        fecha_carpeta = post.fecha_envio.date() if post.fecha_envio else date.today()
        if adjunto is not None:
            ruta = self._raw.guardar(
                adjunto[0], adjunto[1], fecha_carpeta, post.vacante_id
            )
        elif post.cuerpo.strip():
            ruta = self._raw.guardar(
                f"{post.vacante_id}.txt",
                post.cuerpo.encode("utf-8"),
                fecha_carpeta,
                post.vacante_id,
            )
        else:
            ruta = None

        if ruta:
            LOG.info("Archivo original guardado en: %s", ruta)
        return ruta

    def _construir_documento(
        self,
        post: Postulacion,
        origen: str | None,
        texto: str,
        estado: str,
        datos_json: dict[str, Any] | None,
        motivo: str | None,
        ruta_raw: str | None,
    ) -> dict[str, Any]:
        return {
            "mensaje_id": post.mensaje_id,
            "id_candidato": uuid4().hex,
            "vacante_id": post.vacante_id,
            "email_remitente": post.remitente,
            "remitente_metadatos": {
                "nombre": post.remitente_nombre,
                "email": post.remitente_email,
                "dominio": post.remitente_dominio,
            },
            "fecha_envio": post.fecha_envio.isoformat() if post.fecha_envio else None,
            "x_mailer": post.x_mailer or None,
            "ruta_archivo_raw": ruta_raw,
            "formato_origen": origen,
            "datos_json": datos_json,
            "texto_crudo": texto if estado in (ESTADO_REINTENTO,) else None,
            "estado_procesamiento": estado,
            "motivo": motivo,
            "fecha_ingesta": datetime.now(timezone.utc).isoformat(),
        }

    # -------------------------------------------------------------- reintento
    def reintentar_pendientes(
        self, detalle: list[dict[str, Any]]
    ) -> Counter[str]:
        """Reintenta la extracción IA sobre los registros 'Pendiente: Reintento IA'."""
        pendientes = self._bd.pendientes_reintento()  # type: ignore[union-attr]
        LOG.info("Registros pendientes de reintento IA: %d", len(pendientes))

        resultado: Counter[str] = Counter()
        for registro in pendientes:
            texto = registro.get("texto_crudo") or ""
            try:
                datos = self._agente.extraer(texto)
            except ErrorAgenteExtractor as exc:
                LOG.warning("Reintento fallido para %s: %s",
                            registro.get("mensaje_id"), exc)
                detalle.append(
                    {
                        "asunto": "REINTENTO",
                        "vacante": registro.get("vacante_id"),
                        "remitente": registro.get("email_remitente"),
                        "estado": ESTADO_REINTENTO,
                        "motivo": str(exc),
                    }
                )
                resultado[ESTADO_REINTENTO] += 1
                continue

            self._bd.actualizar_tras_reintento(
                registro["mensaje_id"],
                {
                    "datos_json": datos,
                    "texto_crudo": None,
                    "estado_procesamiento": ESTADO_LISTO,
                    "motivo": None,
                    "fecha_reintento": datetime.now(timezone.utc).isoformat(),
                },
            )
            LOG.info("Reintento exitoso: %s -> %s",
                     registro.get("vacante_id"), ESTADO_LISTO)
            detalle.append(
                {
                    "asunto": "REINTENTO",
                    "vacante": registro.get("vacante_id"),
                    "remitente": registro.get("email_remitente"),
                    "estado": ESTADO_LISTO,
                    "motivo": None,
                }
            )
            resultado[ESTADO_LISTO] += 1
        return resultado

    def cerrar(self) -> None:
        if self._bd is not None:
            self._bd.cerrar()