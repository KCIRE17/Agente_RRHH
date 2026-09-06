# AGENTS — Agente RRHH

Guía de estructura y convenciones para agentes de IA que trabajen en este
repositorio. Leer antes de modificar código.

> La documentación completa del proyecto (visión, requerimientos,
> arquitectura, especificación, configuración y uso) vive en **`README.md`**.
> El estado del trabajo y pendientes se controla en **`PENDIENTES.md`**.

## Estructura del proyecto (resumen)

```
Agente_RRHH/
├── main.py                    # CLI raíz (punto de entrada único)
├── pyproject.toml             # dependencias (uv)
├── .env                       # credenciales (NO subir a git)
├── README.md                  # documentación completa del proyecto
├── PENDIENTES.md              # bitácora Scrum (pendientes / checkpoints)
├── AGENTS.md                  # este archivo
├── logs/                      # logs de ejecución (ingesta.log)
├── prompt/                    # prompts de IA editables (.md)
├── data/                      # datos candidatos (archi. medallion) — NO a git
│   ├── bronze/                # originales brutos por <fecha>/<vacante>/
│   ├── silver/candidatos/     # <sha1(mensaje_id)>.json (idempotente)
│   └── gold/                  # evaluaciones/rankings (F2+)
└── src/agente_rrhh/
    ├── core/                  # base común a TODAS las fases (config,
    │                          # json_store, sanitizer, raw_store, logging_setup)
    ├── ingestion/             # FASE 1 — Ingesta y Extracción (Agente 1)
    ├── evaluation/            # FASE 2 — Match Score (Agente 2) [ESQUELETO]
    ├── dashboard/             # FASE 3 — Streamlit [ESQUELETO]
    └── chatbot/               # FASE 4 — Chatbot de consultas [ESQUELETO]
```

## Convenciones

- **`core/` es el denominador común**: configuración, persistencia y utilidades
  viven ahí para que ninguna fase duplique lógica.
- **Fases separadas**: cada fase vive en su subpaquete. Se PERMITE que una fase
  importe código de otra — pero si algo es útil a varias, se promueve a `core/`.
- **Imports relativos** dentro del paquete: `from ..core.config import ...`.
- **Punto de entrada único**: `main.py` en la raíz. Los comandos de uso se
  documentan en `README.md`.
- **Credenciales**: únicamente en `.env`; nunca hardcodear ni loguear secretos.
- **Estados de procesamiento** (definidos en `core/config.py`):
  `Listo para Evaluación`, `Error: Archivo Ilegible`,
  `Error: Formato No Permitido`, `Pendiente: Reintento IA`.
- **Ejecución**: usar `uv run python main.py` (uv gestiona el entorno).
- **Archivos personales**: `data/` y `logs/` no se suben a git
  (datos personales de candidatos).
- **Pendientes**: al avanzar, reflejar el progreso en `PENDIENTES.md`
  (metodología Scrum del proyecto).

## Verificación rápida

```bash
uv run python -m compileall -q src main.py
uv run python main.py --dry-run        # simula la ingesta sin gastar cuota
uv run python main.py limpiar          # purga bronze (retención de .env)
```