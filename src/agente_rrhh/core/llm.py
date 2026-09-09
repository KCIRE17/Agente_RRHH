"""Fachada unica de modelos de IA (Gemini F1, Groq F2) con medicion de tokens.

Un solo punto de entrada ``generar_texto`` para hablar con cualquiera de los
proveedores configurados. Cada llamada devuelve ademas los tokens consumidos,
para auditar el uso por fase.
"""

from __future__ import annotations

import logging
from functools import lru_cache
from typing import Any

LOG = logging.getLogger("agente_rrhh")

PROVEEDOR_GEMINI = "gemini"
PROVEEDOR_GROQ = "groq"

_URL_GROQ = "https://api.groq.com/openai/v1"

PROVEEDORES = {PROVEEDOR_GEMINI, PROVEEDOR_GROQ}


class ErrorModelo(Exception):
    """Fallo de la llamada a la IA (red, cuota, respuesta invalida)."""


@lru_cache(maxsize=4)
def _cliente_gemini(api_key: str) -> Any | None:
    from google.genai import Client

    return Client(api_key=api_key) if api_key else None


@lru_cache(maxsize=4)
def _cliente_groq(api_key: str) -> Any | None:
    from openai import OpenAI

    return OpenAI(api_key=api_key, base_url=_URL_GROQ) if api_key else None


def _uso_gemini(respuesta: Any) -> dict[str, int]:
    md = getattr(respuesta, "usage_metadata", None)
    if md is None:
        return {"prompt": 0, "completado": 0, "total": 0}
    return {
        "prompt": getattr(md, "prompt_token_count", 0) or 0,
        "completado": getattr(md, "candidates_token_count", 0) or 0,
        "total": getattr(md, "total_token_count", 0) or 0,
    }


def _uso_groq(respuesta: Any) -> dict[str, int]:
    uso = getattr(respuesta, "usage", None)
    if uso is None:
        return {"prompt": 0, "completado": 0, "total": 0}
    return {
        "prompt": getattr(uso, "prompt_tokens", 0) or 0,
        "completado": getattr(uso, "completion_tokens", 0) or 0,
        "total": getattr(uso, "total_tokens", 0) or 0,
    }


def generar_texto(
    proveedor: str,
    modelo: str,
    api_key: str,
    prompt: str,
    *,
    temperature: float = 0.2,
    formato_json: bool = True,
) -> tuple[str, dict[str, int]]:
    """Hace una sola llamada al proveedor y devuelve (texto, uso_tokens).

    ``formato_json`` (default True) fuerza ``response_format=json_object`` en
    proveedores OpenAI-compatibles; ponlo en False para respuestas de chat en
    texto libre.
    """
    if proveedor not in PROVEEDORES:
        raise ErrorModelo(f"Proveedor de IA no soportado: {proveedor}")
    if not api_key:
        raise ErrorModelo(
            f"Falta la API key del proveedor '{proveedor}' en el archivo .env."
        )
    LOG.debug("Llamada IA -> proveedor=%s modelo=%s", proveedor, modelo)
    if proveedor == PROVEEDOR_GEMINI:
        return _llamar_gemini(modelo, api_key, prompt, temperature)
    return _llamar_groq(modelo, api_key, prompt, temperature, formato_json)


def _llamar_gemini(
    modelo: str, api_key: str, prompt: str, temperature: float
) -> tuple[str, dict[str, int]]:
    cliente = _cliente_gemini(api_key)
    if cliente is None:
        raise ErrorModelo("No se pudo construir el cliente Gemini.")
    try:
        respuesta = cliente.models.generate_content(
            model=modelo,
            contents=prompt,
            config={"temperature": temperature},
        )
    except Exception as exc:
        raise ErrorModelo(f"Fallo la llamada a Gemini ({modelo}): {exc}") from exc
    texto = respuesta.text or ""
    if not texto.strip():
        raise ErrorModelo("Gemini devolvio una respuesta vacia.")
    return texto, _uso_gemini(respuesta)


def _llamar_groq(
    modelo: str,
    api_key: str,
    prompt: str,
    temperature: float,
    formato_json: bool = True,
) -> tuple[str, dict[str, int]]:
    cliente = _cliente_groq(api_key)
    if cliente is None:
        raise ErrorModelo("No se pudo construir el cliente Groq.")
    try:
        opciones: dict[str, Any] = {
            "model": modelo,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": temperature,
        }
        if formato_json:
            opciones["response_format"] = {"type": "json_object"}
        respuesta = cliente.chat.completions.create(**opciones)
    except Exception as exc:
        raise ErrorModelo(f"Fallo la llamada a Groq ({modelo}): {exc}") from exc
    texto = (
        respuesta.choices[0].message.content if respuesta.choices else ""
    ) or ""
    if not texto.strip():
        raise ErrorModelo("Groq devolvio una respuesta vacia.")
    return texto, _uso_groq(respuesta)