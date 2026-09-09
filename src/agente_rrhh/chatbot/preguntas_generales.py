"""Preguntas y respuestas generales del chatbot (sin IA, costo $0).

Se usan como fallback cuando el proveedor opcional de IA no esta disponible o
cae: el chat avisa y ofrece estas opciones generales con repuestas en codigo.
"""

from __future__ import annotations

from .motor import normalizar

_PAREADAS: list[tuple[list[str], str, str]] = [
    (
        ["QUE ES ESTE SISTEMA", "QUE HACE EL PROYECTO", "QUE ES ESTO", "COMO FUNCIONA"],
        "¿Que es este sistema?",
        "Es el agente de RRHH: ingiere postulaciones desde Gmail (F1), las "
        "convierte en JSON estandarizado, las evalua con un match score 50/30/20 "
        "(F2), las muestra en el dashboard (F3) y ahora responde consultas "
        "operativas en lenguaje natural (F4).",
    ),
    (
        ["QUE ES EL MATCH SCORE", "SCORE", "PUNTAJE DE COMPATIBILIDAD", "COMO SE CALCULA"],
        "¿Como se calcula el puntaje de compatibilidad?",
        "Peso fijo de 50% habilidades, 30% experiencia y 20% formacion "
        "academica. Cada bloque puntua 0-100, se multiplica por su peso y el "
        "resultado se ajusta a 0-100. Clasificacion: Alta (80-100), Media "
        "(50-79) y Baja (< 50).",
    ),
    (
        ["QUE SIGNIFICA ALTA", "MEDIA", "BAJA", "CLASIFICACION"],
        "¿Que significan los niveles Alta, Media y Baja?",
        "Alta pasa a fase tecnica. Media requiere revision manual de fortalezas "
        "y brechas. Baja no avanza en el proceso.",
    ),
    (
        ["COSTO", "GRATIS", "CUOTA", "CERO", "PRECIO", "PAGAR"],
        "¿El chat cuesta dinero?",
        "No. El motor responde 100% en codigo (0 tokens). La IA opcional usa "
        "capas gratuitas y solo si se habilita; los costos estimados se ven en "
        "el panel Costos.",
    ),
    (
        ["DONDE SE GUARDAN", "PRIVACIDAD", "DATOS PERSONALES", "SEGURIDAD", "ALMACENAMIENTO"],
        "¿Donde se guardan los datos de los candidatos?",
        "En tu maquina local, en capas bronze/silver/gold dentro de data/ "
        "(excluidas de git). El servidor del chat solo escucha en localhost.",
    ),
    (
        ["PROVEEDOR", "MODELO", "LLM", "IA", "GROQ", "GEMINI", "OPENAI"],
        "¿Que proveedores de IA usa?",
        "F1 usa Gemini, F2 usa Groq y el chat F4 usa el motor interno; la "
        "narrativa opcional del chat puede apuntar a cualquier proveedor "
        "configurado en .env (PROVEEDOR_CHAT/MODELO_CHAT).",
    ),
    (
        ["ERROR", "FALLO", "NO LEE", "ILEGIBLE", "FORMATO", "PROBLEMA"],
        "¿Que pasa si un archivo no se puede leer?",
        "El candidato queda con 'Error: Archivo Ilegible' o 'Formato No "
        "Permitido' y se registra en la pipeline para revision manual.",
    ),
    (
        ["REQUISITOS", "VACANTE", "CONFIG"],
        "¿Donde se definen los requisitos por vacante?",
        "En config/vacantes/<SLUG>.json; son la regla de negocio editable sin "
        "tocar codigo.",
    ),
]


def buscar(pregunta: str) -> dict[str, str] | None:
    """Empareja una pregunta con una respuesta general (None si no hay match)."""
    n = normalizar(pregunta)
    for claves, pregunta_mostrable, respuesta in _PAREADAS:
        if any(clave in n for clave in claves):
            return {"pregunta": pregunta_mostrable, "respuesta": respuesta}
    return None


def todas() -> list[dict[str, str]]:
    return [
        {"pregunta": pregunta, "respuesta": respuesta}
        for _, pregunta, respuesta in _PAREADAS
    ]