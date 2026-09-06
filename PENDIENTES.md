# PENDIENTES — Bitácora Scrum del Agente RRHH

Checkpoint de estado del proyecto y trabajo pendiente, organizado por fases.
Actualizar este archivo al cerrar o abrir una tarea.

---

## Metodología (cómo se usa)

- Cada tarea avanza por el flujo: **Backlog → En progreso → Hecho**.
- Prioridad: 🔴 Alta · 🟡 Media · 🔵 Baja.
- Una tarea se marca **Hecho** solo cuando cumple su **criterio de
  aceptación** y pasa verificación (`uv run python -m compileall -q src
  main.py` + prueba correspondiente).
- Historial de checkpoints con fecha al cierre de cada hito.

---

## FASE 1 — Ingesta y Extracción de Candidaturas (Agente 1) ✅

### Hecho

- [x] **Conexión IMAP a Gmail** (SSL 993, App Password, respaldo
  `PASSWORD`). *Aceptación: login y búsqueda funcionan en vivo.*
- [x] **Filtro dinámico** `ASUNTO` + `DIAS_ATRAS` con búsqueda en servidor
  (primera palabra + ventana de fecha) y verificación local del prefijo.
- [x] **`BODY.PEEK[]`** para no marcar correos como leídos al inspeccionar.
- [x] **Extracción** de PDF/DOCX/TXT/MD + fallback al cuerpo del correo.
- [x] **Matriz de errores**: `Error: Archivo Ilegible`,
  `Error: Formato No Permitido`.
- [x] **Sanitización** (UTF-8, sin tildes, sin espacios redundantes).
- [x] **Agente Extractor (Gemini)**: texto → JSON estandarizado, mapeo de
  sinónimos y **exclusión de atributos de sesgo**. Prompt editable en
  `prompt/extractor.md`. Modo `--dry-run` verificado.
- [x] **Persistencia JSON (capa silver)** con `sha1(mensaje_id).json`
  (idempotencia por archivo) — `data/silver/candidatos/`.
- [x] **`data/bronze/<fecha>/<vacante>/<archivo>`** idempotente + metadatos del
  remitente (`{nombre, email, dominio}`, `fecha_envio`, `x_mailer`).
- [x] **Reestructuración por fases** (`core/`, `ingestion/`, `evaluation/`,
  `dashboard/`, `chatbot/`) verificada.
- [x] **Documentación consolidada** (`README.md` único + este `PENDIENTES.md`
  + `AGENTS.md`).
- [x] **Fixed 7 bugs críticos**: multi-adjunto (prueba todos + cuerpo),
  `try/except` del lote, `HORA_INGESTA` desde Config, `motivo` consistente,
  reintentos en `detalle`, Message-ID vacío con hash de respaldo, `.gitignore`
  con `data/` y `logs/`.
- [x] **Purga de bronze**: `uv run python main.py limpiar [--dias N]` deduplica
  copias `_<uuid>` y borra originales viejos (`RAWDATA_RETENCION_DIAS`).
- [x] **Arquitectura medallion en `data/`** (bronze/silver/gold) en reemplazo
  de MongoDB (`pymongo` fuera del proyecto).

### Configuración ✅

- [x] 🔴 `GEMINI_API_KEY` en `.env` — configurada (aistudio.google.com/apikey).
- [x] 🟡 `API_EMAIL`/`PASSWORD` vigentes — conexión IMAP probada en vivo.
- [x] 🟡 `MODELO_GEMINI` — `gemini-3.5-flash` (estable): `gemini-2.5-flash` y
  `gemini-flash-latest` quedaron obsoletos/saturados para claves nuevas.

> Lote real (2026-09-06): pipeline IMAP → extracción → Gemini (`gemini-3.5-flash`)
> → `data/silver/candidatos/` ejecutado sin errores con el candidato real
> ANALISTA DE DATOS (PDF en `data/bronze/`, JSON "Listo para Evaluación").

### Backlog / mejoras futuras F1

- [ ] 🟡 **Lote "desde la última ejecución"**: rastrear la última fecha
  procesada en silver en lugar de depender de `DIAS_ATRAS` (evita perder
  correos si no corre un día).
- [ ] 🔵 **Reintento automático de `Pendiente: Reintento IA`** dentro del
  mismo lote (backoff) en lugar de esperar al siguiente.
- [ ] 🔵 **Resumen de vacantes**: reporte por `vacante_id` del total y
  desglose de estados por lote.
- [ ] 🔵 **Alertas en logs** cuando un archivo ilegible o formato no permitido
  requiera revisión manual.

---

## FASE 2 — Evaluación y Match Score (Agente 2) ✅

### Hecho

- [x] 🔴 **Ponderación fija 50/30/20**: Habilidades (50 %), Experiencia
  (30 %), Formación académica (20 %) — `evaluation/reglas.py`.
  *Aceptación: el puntaje se compone con estos pesos y los parciales se
  suman a 100.*
- [x] 🔴 **Match Score 0–100** y clasificación: **Alta (80–100)**, **Media
  (50–79)**, **Baja (< 50)** — calculados en código, con clamps a 0–100.
- [x] 🟡 **Requisitos por vacante** como regla de negocio editable y
  versionable en `config/vacantes/<SLUG>.json` (ej. `ANALISTA_DE_DATOS.json`
  con esenciales/opcionales, `experiencia_minima_anos` y carreras).
- [x] 🟡 **Fortalezas y brechas**: reporte de la IA de requisitos cumplidos y de
  campo obligatorio ausente (`requisito_esencial_ausente`) con puntaje 0.
- [x] 🟡 **Mitigación de sesgos**: el cálculo solo puntúa habilidades,
  experiencia y formación; los datos de contacto (nombre, teléfono, correo)
  van al gold sin participar en la puntuación.
- [x] 🟡 **Modelo de IA**: **Groq** (tier "Forever Free") vía SDK `openai`
  con `response_format=json`; default `openai/gpt-oss-120b` (los `llama-3.3-*`
  no están habilitados en esta cuenta; se listan vía `GET /models`).
  **1 llamada por candidato**; `uso_tokens` guardado en el doc gold.
- [x] 🟡 **Core promotido para F2**: `core/llm.py` (fachada Gemini/Groq +
  tokens), `core/prompts.py` (prompts `.md` + parseo JSON tolerante),
  `core/vacantes.py`, `core/gold_store.py` (escritura atómica + ranking).
- [x] 🟡 **Comando CLI**: `uv run python main.py evaluar [--vacante X]`.
  *Aceptación: escribe `match_score`, `clasificacion`, fortalezas, brechas y
  `uso_tokens` en `data/gold/evaluacion/<vacante>/<id>.json` + `ranking.json`.*
- [x] 🟡 **Idempotencia**: un candidato ya evaluado se omite; fallos de IA van a
  `Pendiente: Reintento Evaluación` y reintentan en el siguiente lote.
- [x] 🔵 **Extracción de contacto en F1**: `datos_contacto`
  (`nombre_completo`, `telefono`, `email`) añadido a `prompt/extractor.md`
  y al JSON silver; re-extraído el candidato real vía Gemini.
- [x] 🔵 **`.gitignore` blindado** para GitHub: `.env.*`, caches, SO/editor,
  temporales; se sigue ignorando `data/` y `logs/` (datos personales).

> Lote real F2 (2026-09-06): `main.py evaluar --vacante "ANALISTA DE DATOS"`
> → el candidato real se evaluó con Groq (`openai/gpt-oss-120b`): score **70**
> **Media**, desglose 50/10/10, `uso_tokens: {prompt 1386, completado 1305,
> total 2691}`; gold + `ranking.json` escritos en `data/gold/evaluacion/`.
> Antes se re-extrajo su silver con `datos_contacto`
> (`telefono: 51956488518`) para el ranking.

> Nota de costo: la sesión F2 real gastó **2 llamadas de LLM** (1 Gemini de
> re-extracción + 1 Groq de evaluación), todas dentro de los free tiers.

### Backlog / mejoras futuras F2

- [ ] 🟡 **Diccionario de habilidades por nivel negocio** (`config/`): definir
  qué nivel de cada herramienta representa valor real para la empresa (hoy la
  coincidencia de habilidades se delega a la IA con `requisitos_evaluados`).
- [ ] 🟡 **Límite de candidatos filtrados** por vacante (regla de negocio).
- [ ] 🔵 **Lote "desde la última ejecución"** compartido con F1 (F1 puede
  perder correos si no corre un día y F2 depende del estado silver).
- [ ] 🔵 **Agregador de tokens**: si el consumo crece, acumular `uso_tokens`
  por fase/lote en un resumen (hoy se controla en el panel del proveedor).

### Definición de listo F2

- [x] Todos los candidatos `Listo para Evaluación` de una vacante tienen
  puntaje, clasificación, fortalezas y brechas documentados; el comando
  cierra con código 0.

---

## FASE 3 — Dashboard y Visualización (Streamlit) 🟡 No iniciada

Carpeta `src/agente_rrhh/dashboard/` (esqueleto).

### Por desarrollar

- [ ] 🟡 **Ranking por vacante**: selector de vacante → candidatos ordenados
  por `match_score`.
- [ ] 🟡 **Detalle del candidato**: habilidades, experiencia, formación,
  certificaciones, fortalezas y brechas.
- [ ] 🟡 **Filtros**: por clasificación (Alta/Media/Baja) y por estado.
- [ ] 🔵 **Resumen visual** del desglose de estados de ingesta.

### Definición de listo F3

- [ ] Responder a una consulta de ranking de una vacante real en menos de 3 s
  desde la interfaz, con los datos de silver/gold.

---

## FASE 4 — Chatbot de consultas RRHH 🟡 No iniciada

Carpeta `src/agente_rrhh/chatbot/` (esqueleto).

### Por desarrollar

- [ ] 🟡 **Consulta sobre el ranking** ("¿quiénes pasan a fase técnica?").
- [ ] 🟡 **Consulta por candidato** (fortalezas, brechas, puntaje).
- [ ] 🟡 **Recomendación de fase técnica** para los candidatos que quedan.

### Definición de listo F4

- [ ] El encargado de RRHH puede responder una pregunta operativa sobre los
  datos mediante lenguaje natural, sin ver la BD.

---

## Historial de checkpoints

| Fecha | Hito | Estado |
| :--- | :--- | :--- |
| 2026-09-05 | F1 implementada y verificada (imap, extracción, Gemini dry-run, silver/raw, metadatos) | ✅ |
| 2026-09-05 | Reestructuración por fases + doc consolidada (README, PENDIENTES, AGENTS) | ✅ |
| 2026-09-06 | F1 end-to-end real (Gemini, prompt de archivo, silver JSON verificados) | ✅ |
| 2026-09-06 | Migración a `data/` medallion (bronze/silver/gold) sin MongoDB; prompts editables; 7 bugs críticos + purga `limpiar`; docs sincronizadas | ✅ |
| 2026-09-06 | F2 end-to-end real: Groq (`openai/gpt-oss-120b`), reglas 50/30/20, requisitos por vacante en `config/`, gold + ranking, `datos_contacto` en F1, `.gitignore` blindado | ✅ |
| — | F2 Match Score funcionando | ⏳ |
| — | F3 Dashboard Streamlit | ⏳ |
| — | F4 Chatbot | ⏳ |