"""Fachada unica de modelos de IA (Gemini, Groq y otros OpenAI-compatibles).

Un solo punto de entrada ``generar_texto`` para hablar con cualquiera de los
proveedores configurados. Cada llamada devuelve ademas los tokens consumidos,
para auditar el uso por fase.

Proveedores soportados:
- ``gemini``     (Google GenAI SDK).
- ``groq``       (OpenAI-compatible).
- ``openrouter`` (OpenAI-compatible).
- ``cerebras``   (OpenAI-compatible).
- ``ollama``     (OpenAI-compatible, local; no requiere API key real).
"""

from __future__ import annotations

import logging
import os
from functools import lru_cache
from typing import Any

LOG = logging.getLogger("agente_rrhh")

PROVEEDOR_GEMINI = "gemini"
PROVEEDOR_GROQ = "groq"
PROVEEDOR_OPENROUTER = "openrouter"
PROVEEDOR_CEREBRAS = "cerebras"
PROVEEDOR_OLLAMA = "ollama"

# Base URL por proveedor OpenAI-compatible. Ollama se resuelve en runtime
# (OLLAMA_BASE_URL) para permitir instancias locales/remotas.
_URLS_OPENAI_COMPAT = {
    PROVEEDOR_GROQ: "https://api.groq.com/openai/v1",
    PROVEEDOR_OPENROUTER: "https://openrouter.ai/api/v1",
    PROVEEDOR_CEREBRAS: "https://api.cerebras.ai/v1",
}
_OLLAMA_BASE_DEFAULT = "http://localhost:11434/v1"

PROVEEDORES_OPENAI_COMPAT = {
    PROVEEDOR_GROQ,
    PROVEEDOR_OPENROUTER,
    PROVEEDOR_CEREBRAS,
    PROVEEDOR_OLLAMA,
}
PROVEEDORES = {PROVEEDOR_GEMINI, *PROVEEDORES_OPENAI_COMPAT}


class ErrorModelo(Exception):
    """Fallo de la llamada a la IA (red, cuota, respuesta invalida)."""


@lru_cache(maxsize=4)
def _cliente_gemini(api_key: str) -> Any | None:
    from google.genai import Client

    return Client(api_key=api_key) if api_key else None


@lru_cache(maxsize=8)
def _cliente_openai_compat(proveedor: str, api_key: str, base_url: str) -> Any | None:
    from openai import OpenAI

    if not api_key:
        return None
    kwargs: dict[str, Any] = {"api_key": api_key, "base_url": base_url}
    if proveedor == PROVEEDOR_OPENROUTER:
        # Identificacion recomendada por OpenRouter (opcional, sin secreto).
        kwargs["default_headers"] = {
            "HTTP-Referer": "https://github.com/KCIRE17/Agente_RRHH",
            "X-Title": "Agente RRHH",
        }
    return OpenAI(**kwargs)


def _base_url(proveedor: str) -> str:
    if proveedor == PROVEEDOR_OLLAMA:
        return (os.getenv("OLLAMA_BASE_URL") or _OLLAMA_BASE_DEFAULT).strip() or (
            _OLLAMA_BASE_DEFAULT
        )
    return _URLS_OPENAI_COMPAT[proveedor]


def _uso_gemini(respuesta: Any) -> dict[str, int]:
    md = getattr(respuesta, "usage_metadata", None)
    if md is None:
        return {"prompt": 0, "completado": 0, "total": 0}
    return {
        "prompt": getattr(md, "prompt_token_count", 0) or 0,
        "completado": getattr(md, "candidates_token_count", 0) or 0,
        "total": getattr(md, "total_token_count", 0) or 0,
    }


def _uso_openai_compat(respuesta: Any) -> dict[str, int]:
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
    proveedor = (proveedor or "").strip().lower()
    if proveedor not in PROVEEDORES:
        raise ErrorModelo(f"Proveedor de IA no soportado: {proveedor}")
    if proveedor == PROVEEDOR_OLLAMA and not api_key:
        api_key = PROVEEDOR_OLLAMA
    if not api_key:
        raise ErrorModelo(
            f"Falta la API key del proveedor '{proveedor}' en el archivo .env."
        )
    LOG.debug("Llamada IA -> proveedor=%s modelo=%s", proveedor, modelo)
    if proveedor == PROVEEDOR_GEMINI:
        return _llamar_gemini(modelo, api_key, prompt, temperature)
    return _llamar_openai_compat(
        proveedor, modelo, api_key, prompt, temperature, formato_json
    )


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


def _llamar_openai_compat(
    proveedor: str,
    modelo: str,
    api_key: str,
    prompt: str,
    temperature: float,
    formato_json: bool = True,
) -> tuple[str, dict[str, int]]:
    cliente = _cliente_openai_compat(proveedor, api_key, _base_url(proveedor))
    if cliente is None:
        raise ErrorModelo(f"No se pudo construir el cliente {proveedor}.")
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
        raise ErrorModelo(f"Fallo la llamada a {proveedor} ({modelo}): {exc}") from exc
    texto = (
        respuesta.choices[0].message.content if respuesta.choices else ""
    ) or ""
    if not texto.strip():
        raise ErrorModelo(f"{proveedor} devolvio una respuesta vacia.")
    return texto, _uso_openai_compat(respuesta)
