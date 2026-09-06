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
│   ├── extractor.md           #   F1: texto → JSON estandarizado
│   └── evaluador.md           #   F2: perfil + requisitos → evaluación
├── config/vacantes/           # requisitos por vacante (regla de negocio)
├── data/                      # datos candidatos (archi. medallion) — NO a git
│   ├── bronze/                # originales brutos por <fecha>/<vacante>/
│   ├── silver/candidatos/     # <sha1(mensaje_id)>.json (idempotente)
│   └── gold/evaluacion/       # <vacante>/<id>.json + ranking.json (F2+)
└── src/agente_rrhh/
    ├── core/                  # base común a TODAS las fases (config,
    │                          # json_store, sanitizer, raw_store, logging_setup,
    │                          # llm, prompts, vacantes, gold_store)
    ├── ingestion/             # FASE 1 — Ingesta y Extracción (Agente 1)
    ├── evaluation/            # FASE 2 — Match Score (Agente 2)
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
  `Error: Formato No Permitido`, `Pendiente: Reintento IA`,
  `Evaluado`, `Pendiente: Reintento Evaluación`.
- **IA por fase, un modelo distinto**: F1 usa Gemini (`MODELO_GEMINI`); F2 usa
  Groq (`MODELO_EVALUADOR`/`PROVEEDOR_EVALUADOR`, default `openai/gpt-oss-120b`)
  a través de la fachada `core/llm.py` (único punto que toca APIs). La cuenta
  Groq no tiene habilitados los `llama-3.3-*`; consultar modelos con
  `GET /openai/v1/models` antes de asumir disponibilidad.
- **1 llamada de IA por candidato** en F2; `uso_tokens` se guarda en el
  documento gold (sin agregador central; el control queda en el panel del
  proveedor).
- **Requisitos por vacante**: solo en `config/vacantes/<SLUG>.json`
  (regla de negocio versionable). Slug = `vacante_id` en mayúsculas sin
  tildes y con espacios → `_`. Candidatos sin requisitos se omiten con aviso.
- **Puntaje y clasificación se calculan en código** (`core`/`evaluation/
  reglas.py`), nunca se cree ciegamente el `match_score` que devuelve la IA
  (pesos 50/30/20, umbrales 80/50, clamps 0–100).
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