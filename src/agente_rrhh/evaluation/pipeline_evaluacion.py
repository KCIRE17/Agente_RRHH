"""Orquestación de la evaluación: silver -> requisitos -> IA -> gold."""

from __future__ import annotations

import json
import logging
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .agente_evaluador import AgenteEvaluador, ErrorAgenteEvaluador
from .reglas import clasificar, componer_puntaje
from ..core import costo as costo_mod
from ..core import habilidades as habilidades_mod
from ..core.config import (
    ESTADO_EVALUADO,
    ESTADO_LISTO,
    Config,
)
from ..core.gold_store import GoldStore
from ..core.json_store import JsonStore
from ..core.llm import PROVEEDOR_GROQ
from ..core.vacantes import ErrorRequisitos, RequisitosVacante, slug_vacante

LOG = logging.getLogger("agente_rrhh")


class PipelineEvaluacion:
    def __init__(
        self,
        cfg: Config,
        dry_run: bool = False,
        vacante: str | None = None,
        re_evaluar: bool = False,
    ) -> None:
        self._cfg = cfg
        self._dry_run = dry_run
        self._vacante = vacante
        self._re_evaluar = re_evaluar
        self._store = JsonStore(cfg.silver_dir)
        self._gold = GoldStore(cfg.gold_dir) if not dry_run else None
        self._requisitos = RequisitosVacante(cfg.rutas_vacantes)
        self._agente = AgenteEvaluador(
            cfg.groq_api_key, cfg.modelo_evaluador, cfg.prompt_evaluador
        )
        self._diccionario = habilidades_mod.cargar_diccionario(
            cfg.diccionario_habilidades
        )

    def ejecutar(self) -> dict[str, Any]:
        resumen: Counter[str] = Counter()
        detalle: list[dict[str, Any]] = []
        tokens_lote = {"prompt": 0, "completado": 0}
        evaluados_por_vacante: Counter[str] = Counter()

        candidatos = self._store.candidatos(estado=ESTADO_LISTO)
        if self._vacante:
            objetivo = slug_vacante(self._vacante)
            candidatos = [
                c for c in candidatos if slug_vacante(c.get("vacante_id", "")) == objetivo
            ]
        LOG.info("Candidatos '%s': %d", ESTADO_LISTO, len(candidatos))

        for cand in candidatos:
            vacante_id = cand.get("vacante_id", "")
            id_cand = cand.get("id_candidato", "")

            # Sin `re_evaluar` se respeta la idempotencia de F2: un candidato con
            # evaluación en gold no se vuelve a llamar a la IA (ahorra cuota).
            if (
                not self._re_evaluar
                and self._gold is not None
                and self._gold.existe_evaluacion(vacante_id, id_cand)
            ):
                LOG.info("Omitido (ya evaluado): %s", id_cand)
                resumen["Omitido (ya evaluado)"] += 1
                continue

            try:
                requisitos = self._requisitos.cargar(vacante_id)
            except ErrorRequisitos as exc:
                LOG.warning("%s", exc)
                resumen["Sin requisitos"] += 1
                continue

            limite = int(requisitos.get("max_candidatos") or 0)
            if limite > 0 and evaluados_por_vacante[vacante_id] >= limite:
                LOG.info(
                    "Omitido (límite de %d por vacante alcanzado): %s %s",
                    limite,
                    vacante_id,
                    id_cand,
                )
                resumen["Omitido (límite por vacante)"] += 1
                continue

            perfil = self._construir_perfil(cand)
            try:
                datos_ia, uso = self._agente.evaluar(
                    perfil,
                    self._requisitos_para_ia(requisitos),
                    dry_run=self._dry_run,
                )
            except ErrorAgenteEvaluador as exc:
                LOG.warning("Fallo la evaluacion de %s: %s", vacante_id, exc)
                resumen["Pendiente: Reintento Evaluación"] += 1
                detalle.append(
                    {
                        "vacante": vacante_id,
                        "id_candidato": id_cand,
                        "estado": "Pendiente: Reintento Evaluación",
                        "motivo": str(exc),
                    }
                )
                continue

            documento = self._construir_documento(cand, requisitos, datos_ia, uso)
            evaluados_por_vacante[vacante_id] += 1
            tokens_lote["prompt"] += int(uso.get("prompt", 0) or 0)
            tokens_lote["completado"] += int(uso.get("completado", 0) or 0)

            if self._dry_run:
                LOG.info("[DRY-RUN] %s -> %s", vacante_id, documento["estado_procesamiento"])
                LOG.info(
                    "JSON evaluacion:\n%s",
                    json.dumps(documento, ensure_ascii=False, indent=2),
                )
            else:
                self._gold.guardar_evaluacion(vacante_id, documento)
                LOG.info(
                    "Evaluado %s (%s): score=%s -> %s",
                    id_cand,
                    vacante_id,
                    documento["match_score"],
                    documento["clasificacion"],
                )

            resumen[documento["estado_procesamiento"]] += 1

        LOG.info("Resumen de evaluacion: %s", dict(resumen))
        self._registrar_resumen_lote(resumen, tokens_lote)
        return {
            "resumen": dict(resumen),
            "detalle": detalle,
            "total": len(candidatos),
            "uso_tokens": dict(tokens_lote),
        }

    def _requisitos_para_ia(self, requisitos: dict[str, Any]) -> dict[str, Any]:
        """Copia los requisitos y añade el diccionario de niveles de habilidad.

        La copia se pasa a la IA (dentro de ``requisitos_vacante``); el original
        sigue guardándose en el gold sin este contexto adicional.
        """
        niveles = habilidades_mod.resumen_para_prompt(self._diccionario)
        if not niveles:
            return requisitos
        enriquecido = dict(requisitos)
        base = dict(enriquecido.get("requisitos") or {})
        base["niveles_habilidad_valorados"] = niveles
        enriquecido["requisitos"] = base
        return enriquecido

    def _registrar_resumen_lote(
        self, resumen: Counter[str], tokens_lote: dict[str, int]
    ) -> None:
        """Acumula el uso de tokens del lote en data/gold/costo/uso_fase2.jsonl."""
        if self._dry_run or self._gold is None:
            return
        candidatos = int(resumen.get(ESTADO_EVALUADO, 0))
        if candidatos == 0 and not tokens_lote["prompt"] and not tokens_lote["completado"]:
            return
        costo_mod.registrar_resumen(
            str(Path(self._cfg.gold_dir) / "costo" / "uso_fase2.jsonl"),
            "evaluacion",
            modelo=self._cfg.modelo_evaluador,
            proveedor=PROVEEDOR_GROQ,
            candidatos=candidatos,
            prompt_tokens=tokens_lote["prompt"],
            completado_tokens=tokens_lote["completado"],
            ruta_tarifas=self._cfg.tarifas_costo,
        )

    # -------------------------------------------------------------------- util
    def _construir_perfil(self, cand: dict[str, Any]) -> dict[str, Any]:
        datos = cand.get("datos_json") or {}
        return {
            "vacante_id": cand.get("vacante_id"),
            "datos_contacto": datos.get("datos_contacto") or {},
            "datos_estructurados": datos.get("datos_estructurados") or {},
        }

    def _construir_documento(
        self,
        cand: dict[str, Any],
        requisitos: dict[str, Any],
        datos_ia: dict[str, Any],
        uso: dict[str, int],
    ) -> dict[str, Any]:
        datos = cand.get("datos_json") or {}
        contacto = datos.get("datos_contacto") or {}
        remitente = cand.get("remitente_metadatos") or {}
        desglose, score = componer_puntaje(datos_ia)

        return {
            "id_candidato": cand.get("id_candidato"),
            "vacante_id": cand.get("vacante_id"),
            "mensaje_id": cand.get("mensaje_id"),
            "nombre_completo": contacto.get("nombre_completo")
            or remitente.get("nombre"),
            "telefono": contacto.get("telefono"),
            "email_remitente": cand.get("email_remitente"),
            "fecha_envio": cand.get("fecha_envio"),
            "match_score": score,
            "clasificacion": clasificar(score),
            "desglose": desglose,
            "fortalezas": datos_ia.get("fortalezas") or [],
            "brechas": datos_ia.get("brechas") or [],
            "requisito_esencial_ausente": datos_ia.get("requisito_esencial_ausente") or [],
            "justificacion": datos_ia.get("justificacion"),
            "requisitos_evaluados": requisitos.get("requisitos") or {},
            "proveedor": PROVEEDOR_GROQ,
            "modelo": self._cfg.modelo_evaluador,
            "uso_tokens": uso,
            "estado_procesamiento": ESTADO_EVALUADO,
            "fecha_evaluacion": datetime.now(timezone.utc).isoformat(),
        }

    def cerrar(self) -> None:
        self._store.cerrar()