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

## FASE 3 — Dashboard y Visualización (Streamlit) ✅

### Hecho

- [x] 🟡 **Lanzamiento integrado**: `uv run python main.py dashboard [--port N]`
  (un solo punto de entrada; `streamlit run src/agente_rrhh/dashboard/app.py`).
- [x] 🟡 **Ranking por vacante**: selector de vacante → postulantes ordenados por
  puntaje de compatibilidad, fila de métricas (Postulantes evaluados,
  Compatibilidad alta/media/baja, Puntaje promedio) y distribución por
  nivel de compatibilidad (`st.bar_chart`).
- [x] 🟡 **Ficha del postulante**: puntaje de compatibilidad, nivel, datos de
  contacto (teléfono/correo), fortalezas, aspectos por reforzar,
  requisito esencial ausente resaltado, resumen del análisis, explicación del
  cálculo 50/30/20 y **hoja de vida unida con silver**.
- [x] 🟡 **Filtros**: por clasificación (Alta/Media/Baja) en el ranking.
- [x] 🔵 **Resumen de postulaciones**: conteo de lo recibido por situación y
  por vacante + aviso de postulaciones pendientes de evaluación.
- [x] 🔵 **Regla visual RRHH**: sugerencia por clasificación (Alta → fase
  técnica, Media → revisión manual, Baja → no avanza).
- [x] 🔵 **Lenguaje del área de talento**: términos técnicos traducidos a la
  interfaz (hoja de vida, aspectos por reforzar, puntaje de compatibilidad,
  postulaciones) + pestaña **Metodología** que explica el cálculo y cada
  situación de forma amigable (estados internos mapeados en `consultas.py`).
- [x] 🔵 **Tema estético**: `.streamlit/config.toml` + CSS propio (tarjetas,
  badges por clasificación, chips de habilidades).
- [x] 🔵 **Capa de datos separada**: `dashboard/consultas.py` (lectura
  gold/silver sin UI), caché 30 s + botón "Actualizar".

> Verificación (2026-09-06): AppTest de Streamlit sin excepciones en las 4
> vistas (Ranking de postulantes + Postulante + Postulaciones + Metodología
> renderizan con el candidato real de ANALISTA DE DATOS, incluidos filtros);
> arranque real `main.py dashboard --port 8510` → `/_stcore/health` = "ok";
> "evaluados" derivado de gold (F2 no muta silver).

### Definición de listo F3

- [x] Responder a una consulta de ranking de una vacante real en menos de 3 s
  desde la interfaz, con los datos de silver/gold.

---

## FASE 4 — Chatbot de consultas RRHH ✅

App web responsiva (FastAPI + SPA) en `src/agente_rrhh/chatbot/`, lanzada con
`uv run python main.py chat [--port N]` (solo localhost). Costo de uso **$0**:
el motor responde 100 % en código y la IA es opcional (`PROVEEDOR_CHAT` vacío =
offline, cero tokens).

### Hecho

- [x] 🔴 **Motor code-first (modo offline default)**: clasificación de intención
  por reglas + datos desde `dashboard.consultas`/`core` y bloques visuales
  (tablas, tarjetas, listas) generados **sin gastar tokens**.
- [x] 🔴 **Contexto ligero**: sesión en memoria que recuerda la entidad en foco
  (vacante/candidato) para seguimientos como "¿su teléfono?". Se resetea con
  "Nuevo chat".
- [x] 🟡 **8 utilidades**: ranking, detalle de candidato, fase técnica,
  pipeline por estado/vacante, brechas de mercado, comparador de candidatos,
  origen por dominio de correo y borradores de comunicación (avance/rechazo).
- [x] 🟡 **Simulador de pesos**: re-pesaje con `desglose` guardado (puro código,
  clamp 0–100, umbrales 80/50), panel con sliders (50/30/20 ↔ alternativos).
- [x] 🟡 **Costos dentro de la app**: momento por llamada de chat en
  `data/gold/costo/uso_chat.jsonl` + suma de `uso_tokens` de F2 (gold) +
  tarifas editables en `config/tarifas.json`. En modo offline = $0.
- [x] 🟡 **IA opcional**: `core/llm.py` admite `formato_json=False` (texto de
  chat); `PROVEEDOR_CHAT`/`MODELO_CHAT` en `.env`; default `groq` con
  `openai/gpt-oss-120b`. Cuando falla o no hay clave, responde offline y avisa.
- [x] 🟡 **Fallback amable**: si no se entiende la consulta, avisa + ofrece
  opciones y respuestas generales (FAQ en `chatbot/preguntas_generales.py`).
- [x] 🟡 **Frontend responsivo**: SPA vanilla (HTML/CSS/JS, sin dependencias en
  el navegador) con vistas Chat, Simulador, Brechas, Costos y Fase técnica.
- [x] 🔵 **Prompt editable** `prompt/chatbot.md` (solo se usa si IA activada).
- [x] 🔵 **Datos sintéticos de prueba**: `tools/generar_datos_prueba.py`
  (**standalone**, no lo ejecuta el proyecto) → `data_pruebas/` (gitignored),
  2 vacantes, 4 evaluados + errores/reintentos; se prueba con
  `DATA_DIR=data_pruebas`.
- [x] 🔵 **Verificación**: `compileall` ok; TestClient sobre `/api/*` con
  `data_pruebas` (ranking, candidato, seguimiento, comparador, brechas, origen,
  borrador, costos, simulador, fallback/FAQ); arranque real `main.py chat`
  → `/api/health` ok; 0 tokens en modo offline.
- [x] 🟡 **Modo demo MVP (Vercel)**: `DEMO_CONSULTAS_IA` (default 3) limita las
  consultas IA por conversación; al agotarse el motor code-first responde con
  datos verificados ($0). Contador visible en la SPA y reseteo con "Nuevo chat".
- [x] 🟡 **Deploy Vercel listo**: `api/index.py` (ASGI `app`), `vercel.json`,
  `runtime.txt` (3.12), `requirements.txt` (subset chatbot), `.vercelignore`,
  `data_demo/` con **30+ candidatos ficticios** generados por
  `tools/generar_datos_demo.py`, `.env.example` y docs en `README.md` §8.

### Definición de listo F4

- [x] El encargado de RRHH responde una pregunta operativa sobre los datos
  mediante lenguaje natural, sin ver la BD, con costo $0 (modo offline) y
  costos/tokens visibles en la app.

### Backlog / mejoras futuras F4

- [ ] 🔵 **Persistencia de sesiones**: pasar el contexto ligero a archivo para
  no perder la entidad en foco al reiniciar el proceso.
- [ ] 🔵 **Historial del chat** opcional (hoy se priva al recargar la página).
- [ ] 🟡 **Modelo de chat fuera de Groq**: al sumar un proveedor (OpenRouter/
  Cerebras/Ollama), añadir su cliente en `core/llm.py` respetando la fachada.

---

## Historial de checkpoints

| Fecha | Hito | Estado |
| :--- | :--- | :--- |
| 2026-09-05 | F1 implementada y verificada (imap, extracción, Gemini dry-run, silver/raw, metadatos) | ✅ |
| 2026-09-05 | Reestructuración por fases + doc consolidada (README, PENDIENTES, AGENTS) | ✅ |
| 2026-09-06 | F1 end-to-end real (Gemini, prompt de archivo, silver JSON verificados) | ✅ |
| 2026-09-06 | Migración a `data/` medallion (bronze/silver/gold) sin MongoDB; prompts editables; 7 bugs críticos + purga `limpiar`; docs sincronizadas | ✅ |
| 2026-09-06 | F2 end-to-end real: Groq (`openai/gpt-oss-120b`), reglas 50/30/20, requisitos por vacante en `config/`, gold + ranking, `datos_contacto` en F1, `.gitignore` blindado | ✅ |
| 2026-09-06 | F3 Dashboard Streamlit end-to-end: `main.py dashboard`, vistas Ranking de postulantes / Postulante / Postulaciones / Metodología en lenguaje de RRHH, tema visual, `consultas.py` (gold+silver), verificado con AppTest + health check | ✅ |
| 2026-09-07 | F4 Chatbot end-to-end: app web responsiva FastAPI + SPA, motor code-first costo $0, 8 utilidades, simulador de pesos, costos/tokens en la app, IA opcional (Groq), fallback + FAQ, datos sintéticos en `data_pruebas/`, verificado con TestClient + health check | ✅ |
| 2026-09-08 | Deploy MVP Vercel listo: modo demo `DEMO_CONSULTAS_IA` (3 IA por conversación → motor offline $0), contador en SPA, `api/index.py` + `vercel.json` + `runtime.txt` + `requirements.txt` + `.vercelignore`, `data_demo/` con 30+ candidatos ficticios (`tools/generar_datos_demo.py`), 2 vacantes nuevas en `config/`, `.env.example`, README §8 | ✅ |