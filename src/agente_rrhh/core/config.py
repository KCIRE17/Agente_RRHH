"""Configuración central: carga y valida las variables del archivo .env."""

from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv

IMAP_HOST = "imap.gmail.com"
IMAP_PUERTO = 993

# Estados registrados en la base de datos (matriz de excepciones del README).
ESTADO_LISTO = "Listo para Evaluación"
ESTADO_ILEGIBLE = "Error: Archivo Ilegible"
ESTADO_FORMATO = "Error: Formato No Permitido"
ESTADO_REINTENTO = "Pendiente: Reintento IA"

PREFIJO_ASUNTO = "POSTULACION - "
EXTENSIONES_PERMITIDAS = {".pdf", ".docx", ".txt", ".md"}


def _parsear_int(valor: str | None, por_defecto: int) -> int:
    try:
        return int(valor) if valor else por_defecto
    except ValueError:
        return por_defecto


@dataclass(frozen=True)
class Config:
    email: str = ""
    password: str = ""
    gemini_api_key: str = ""
    modelo_gemini: str = "gemini-3.5-flash"
    asunto: str = PREFIJO_ASUNTO
    dias_atras: int = 1
    data_dir: str = "data"
    prompt_extractor: str = "prompt/extractor.md"
    retencion_dias: int = 90
    hora_ingesta: str = "18:00"
    imap_timeout: int = 30

    # ------------------------------------------------------------------ rutas
    @property
    def bronze_dir(self) -> str:
        return os.path.join(self.data_dir, "bronze")

    @property
    def silver_dir(self) -> str:
        return os.path.join(self.data_dir, "silver")

    @property
    def gold_dir(self) -> str:
        return os.path.join(self.data_dir, "gold")

    def validar(self) -> list[str]:
        """Devuelve la lista de variables requeridas que faltan."""
        faltantes = []
        if not self.email:
            faltantes.append("EMAIL")
        if not self.password:
            faltantes.append("API_EMAIL/PASSWORD")
        return faltantes

    @classmethod
    def desde_env(cls) -> "Config":
        load_dotenv()
        app_password = os.getenv("API_EMAIL", "").strip() or os.getenv(
            "PASSWORD", ""
        ).strip()
        return cls(
            email=os.getenv("EMAIL", "").strip(),
            password=app_password,
            gemini_api_key=os.getenv("GEMINI_API_KEY", "").strip(),
            modelo_gemini=os.getenv("MODELO_GEMINI", "gemini-3.5-flash").strip(),
            asunto=(os.getenv("ASUNTO") or PREFIJO_ASUNTO).strip() or PREFIJO_ASUNTO,
            dias_atras=_parsear_int(os.getenv("DIAS_ATRAS"), 1),
            data_dir=(os.getenv("DATA_DIR") or "data").strip() or "data",
            prompt_extractor=(
                os.getenv("PROMPT_EXTRACTOR") or "prompt/extractor.md"
            ).strip()
            or "prompt/extractor.md",
            retencion_dias=_parsear_int(os.getenv("RAWDATA_RETENCION_DIAS"), 90),
            hora_ingesta=(os.getenv("HORA_INGESTA") or "18:00").strip() or "18:00",
            imap_timeout=_parsear_int(os.getenv("IMAP_TIMEOUT"), 30),
        )