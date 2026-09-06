"""Agente RRHH — Módulo de Ingesta, Evaluación, Dashboard y Chatbot.

Fases:
    1. Ingesta y Extracción (IMAP -> extracción -> sanitización -> Gemini -> silver).
    2. Evaluación y Match Score (gold).
    3. Dashboard Streamlit.
    4. Chatbot de consultas RRHH.

Persistencia: arquitectura medallion en `data/` (bronze/silver/gold).
"""

__version__ = "0.1.0"