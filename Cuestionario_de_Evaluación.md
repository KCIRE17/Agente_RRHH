# Cuestionario de Evaluación — Proyecto Final de Tecnologías Emergentes (Sistema Multiagente)

**Proyecto:** Agente RRHH — Sistema Multiagente de Preselección de Talento
**Fecha de elaboración:** Oct 10, 2026 (actualizado con el MVP final)
**Repositorio:** https://github.com/KCIRE17/Agente_RRHH · **Sistema en línea:** https://agente-rrhh-five.vercel.app/

> Nota: por seguridad no se incluye ninguna clave, contraseña ni token; sólo se
> indican **nombres de variables de entorno**. Los datos en línea son **ficticios**
> (`data_demo/`).

---

## A. Datos del integrante y del equipo

**A1. Código y nombres completos del integrante**
- 2022016648 — Alvitrez Daviran Josmelll Kevin
- 2022016479 — Ilares Llanos Erick

**A2. Número de grupo**
- Grupo 7

**A3. Integrantes del equipo y rol de cada uno**
- Ilares Llanos Erick — Investigador Principal
- Alvitrez Daviran Josmelll Kevin — Investigador Secundario

**A4. Nombre del proyecto / producto**
Agente RRHH — Sistema Multiagente de Preselección de Talento. Automatiza el cribado de CVs: recibe postulaciones por correo (Gmail vía IMAP), las estandariza con IA (Agente 1, Gemini), las evalúa contra los requisitos de cada vacante (Agente 2, Groq) y expone ranking, fichas, brechas, costos y consultas en lenguaje natural (F3 dashboard Streamlit + F4 chatbot FastAPI).

**A5. URL pública del sistema en línea (HTTPS)**
🔗 **https://agente-rrhh-five.vercel.app/**

Desplegado en Vercel (plan Hobby, `@vercel/python`). El sistema está en línea y responde
`GET /api/health` → **HTTP 200** con `{"ok": true, "modo": "groq", "data_dir": "data_demo", ...}`,
además de `/api/vacantes`, `/api/ranking`, `/api/traza` y la SPA. El modo puede dejarse en
**offline ($0)** vaciando la variable `PROVEEDOR_CHAT` en Vercel (Settings → Environment Variables).
Configuración del deploy: `vercel.json`, `api/index.py`, `runtime.txt` (3.12), `requirements.txt`
y `data_demo/` con 30+ candidatos ficticios (README §8).

**A6. URL del repositorio de GitHub**
https://github.com/KCIRE17/Agente_RRHH (rama `main`, público, 8 commits: `44c7604`, `df99580`, `c668aa6`, `dd1bc28`, `c039bd0`, `73ab8ca`, `8513bf3`, `fc71719`).

**A7. URL del video demostrativo (3 a 5 minutos)**
PENDIENTE DE EQUIPO: grabar el video de 3–5 min mostrando el flujo F1→F2→F3→F4 (ingesta, evaluación, dashboard, chat) y la URL en línea, subirlo a YouTube/Drive y pegar el enlace aquí.

---

## B. Problema, usuario e innovación

**B1. ¿Qué problema concreto resuelve el proyecto y para quién? Incluye un dato o evidencia.**
Resuelve la preselección de talento: leer decenas de CVs, extraer a mano los datos relevantes y compararlos contra los requisitos de la vacante de forma subjetiva y sin trazabilidad. Usuario: el encargado del área de talento / RRHH de una empresa (usuario, sector reclutamiento).
Evidencia del problema: el sistema procesa hasta ~30 CVs diarios por correo (README §2.1) y, en el lote real procesado, sólo 3 de los 10 evaluados de la vacante ANALISTA DE DATOS resultaron de compatibilidad Alta (score ≥ 80): sin cribado automático, la mayoría de las postulaciones son ruido que el analista debe revisar. Ver ranking en `data_demo/gold/evaluacion/ANALISTA_DE_DATOS/ranking.json`.

**B2. ¿Cómo se resuelve hoy ese problema y qué limitaciones tiene la solución actual?**
Hoy el reclutador lee cada CV en la bandeja de correo, vuelca manualmente habilidades y experiencia y compara a ojo contra el puesto; cada evaluador pondera distinto y no queda un puntaje objetivo ni auditable. Limitaciones: es lento y no escala (30+ CVs/día), deja sesgos implícitos (foto, edad, género, domicilio), no estandariza formatos (cada CV se redacta distinto) y no documenta el criterio.

**B3. ¿Qué hace innovador a su proyecto? Diferencia con al menos tres soluciones existentes.**
Es un sistema multiagente de IA (IA agéntica) con un agente por etapa, cada uno con el modelo y proveedor más adecuado, que entrega un match score 50/30/20 DETERMINISTA (la IA propone, el código decide), bloquea el sesgo por diseño y funciona a costo $0 (free tiers).
Diferencias frente a soluciones existentes:
1. **LinkedIn Talent Solutions / LinkedIn Recruiter** (https://www.linkedin.com/business/talent-solutions): es un ATS de pago que prioriza perfiles de su propia red; no evalúa contra los requisitos editables de tu vacante, no tiene pipeline multiagente propio y no bloquea sesgo por diseño.
2. **Greenhouse / Workable** (https://www.greenhouse.com, https://www.workable.com): gestionan postulaciones y workflow, pero la comparación contra requisitos es manual/configurada y no estandariza CVs con IA ni calcula un puntaje auditable 50/30/20.
3. **Frameworks de agentes genéricos** (AutoGen / CrewAI, https://microsoft.github.io/autogen/): son librerías, no una solución puntual; aquí la coordinación es código propio sobre pipelines con persistencia medallion, regla de negocio versionable (`config/vacantes`) y costo $0.

**B4. ¿Qué categoría de tecnología emergente aplica y por qué?**
IA agéntica e hiperautomatización: múltiples agentes de IA especializados (Agente 1 extractor con Gemini, Agente 2 evaluador con Groq, Agente 3 asistente code-first con IA opcional) que automatizan un proceso de negocio completo de extremo a extremo (correo → CV estructurado → puntaje → ranking → consulta). Es la adecuada porque el proceso tiene etapas claramente separables donde cada agente usa el mejor modelo/proveedor según calidad, costo y latencia (README §2, §5, §8).

**B5. ¿Qué resultado medible esperan lograr? ¿Cómo lo van a medir?**
Reducir el tiempo de cribado de una vacante de varias horas (lectura manual de ~30 CVs) a un ranking listo en minutos, con puntaje objetivo y trazable. Medición: (1) F2 evalúa 10 candidatos en ~2 min con limitación del free tier de Groq (log 2026-09-26); (2) el dashboard F3 responde una consulta de ranking en <3 s (criterio de listo de F3 verificado); (3) costo por evaluación documentado con `uso_tokens` y tarifas (`config/tarifas.json`); (4) % de candidatos clasificados correctamente según regla de negocio (ver I2).

**B6. Objetivo general y objetivos específicos (máximo tres).**
General: automatizar la preselección de candidatos mediante un sistema multiagente que extrae, estandariza, evalúa y consulta perfiles sin sesgo y a costo $0.
Específicos:
1. (F1) Ingerir CVs desde el correo y estandarizarlos a JSON con IA (Agente 1, Gemini).
2. (F2) Calcular match score 50/30/20 y ranking por vacante con IA (Agente 2, Groq) y reglas deterministas en código.
3. (F3/F4) Exponer ranking, fichas, brechas, costos, simulador de pesos y consultas en lenguaje natural al área de RRHH.

---

## C. Requerimientos funcionales

**C1. Tabla de requerimientos funcionales (mínimo 8, priorizados)**

| Código | Requerimiento funcional | Prioridad | Agente(s) responsable(s) | Criterio de aceptación verificable |
| :--- | :--- | :--- | :--- | :--- |
| RF-01 | Ingestar postulaciones desde Gmail (IMAP SSL, asunto `POSTULACION - <vacante>`, BODY.PEEK) | Alta | Agente 1 | Un correo con el asunto y adjunto PDF/DOCX/TXT/MD genera su JSON en `data/silver` con estado "Listo para Evaluación". Verificado 2026-09-06. |
| RF-02 | Extraer texto de PDF/DOCX/TXT/MD y sanitizarlo (UTF-8, sin tildes) | Alta | Agente 1 | pdfplumber/python-docx extraen; PDFs de imagen/corruptos van a "Error: Archivo Ilegible" sin gastar IA. |
| RF-03 | Estandarizar el CV a JSON (datos_contacto + datos_estructurados + control_sesgo) | Alta | Agente 1 | El JSON silver sigue el esquema (habilidades, experiencia_laboral, formacion_academica, certificaciones) y excluye foto/edad/género/dirección/estado_civil. |
| RF-04 | Evaluar perfil vs. requisitos por vacante (match score IA) | Alta | Agente 2 | 1 llamada Groq por candidato; se guarda desglose, fortalezas, brechas, requisito esencial ausente en `data/gold`. |
| RF-05 | Calcular clasificación determinista (Alta≥80, Media≥50, Baja<50) | Alta | Agente 2 + `reglas.py` | Score y clasificación se calculan en código (no del JSON crudo de la IA), con clamps 0–100. |
| RF-06 | Generar ranking por vacante | Alta | Agente 2 | `ranking.json` ordenado desc con `vacante_id`, total y candidatos; recalculado con escritura atómica. |
| RF-07 | Dashboard F3: Ranking / Postulante / Postulaciones / Metodología | Media | Agente 2 (datos) + Streamlit | Vista ranking de una vacante responde <3 s; AppTest sin excepciones y `/_stcore/health` = ok. |
| RF-08 | Chatbot F4: consultas en lenguaje natural (ranking, candidato, fase técnica, brechas, origen, borrador, costos) | Media | Agente 3 (motor code-first) | `/api/chat` responde con datos verificados de silver/gold; modo offline 0 tokens y fallback amable. |
| RF-09 | Simulador de pesos (re-pesaje 50/30/20 ↔ alternativos) | Baja | Agente 3 | `/api/simular` recalcula usando el desglose guardado, con clamp 0–100 y umbrales 80/50, sin llamar a la IA. |
| RF-10 | Login en F4 con token Bearer (12 h) y logout | Media | Agente 3 (FastAPI) | Con `ADMIN_USUARIO`/`ADMIN_CLAVE`, `/api/*` devuelve 401 sin token; `/api/login` emite token; comparación con `hmac.compare_digest`. |
| RF-11 | Bitácora de costos por consulta IA | Baja | `core/costo.py` | Cada llamada IA del chat se registra en `data/gold/costo/uso_chat.jsonl` con tokens y costo estimado; offline = $0. |
| RF-12 | Trazabilidad de datos por candidato | Media | Agente 3 (FastAPI) | `GET /api/traza` devuelve el recorrido correo → silver (F1) → gold/ranking (F2) → chat (F4) por candidato; visible en la vista "Traza del dato" de la SPA. |

**C2. Describe el flujo principal de uso paso a paso**
1. El candidato envía su CV por correo a la cuenta de postulaciones con asunto `POSTULACION - <puesto>`.
2. `main.py` (lote programado a `HORA_INGESTA=18:00` o manual) conecta por IMAP SSL, filtra UNSEEN + asunto + fecha en el servidor y lee los adjuntos con BODY.PEEK (no marca correos como leídos).
3. Se extrae el texto (PDF/DOCX/TXT/MD; fallback al cuerpo del correo) y se sanitiza.
4. Agente 1 (Gemini, `prompt/extractor.md`) estandariza el texto a JSON y se guarda en `data/silver/candidatos/<sha1(mensaje_id)>.json` (idempotente).
5. `main.py evaluar`: Agente 2 (Groq, `prompt/evaluador.md`) evalúa el perfil contra `config/vacantes/<SLUG>.json`; `reglas.py` compone el score 50/30/20 y la clasificación y se escribe `data/gold/evaluacion/<vacante>/<id>.json` + `ranking.json`.
6. El usuario de RRHH abre el dashboard F3 (ranking por vacante) o pregunta al chatbot F4 en lenguaje natural y recibe el resultado: puntaje, nivel, fortalezas, brechas y la sugerencia de regla (Alta → fase técnica, Media → revisión manual, Baja → no avanza).

**C3. Lista los actores del sistema y qué puede hacer cada uno**
- **Candidato:** envía su CV por correo (única interacción; no ingresa al sistema).
- **Encargado/a de RRHH (usuario):** consulta dashboard F3 y chatbot F4, revisa fichas y aprueba el siguiente paso (los borradores de avance/rechazo los redacta el sistema pero los envía una persona). No requiere registro; el login de F4 es opcional.
- **Agente 1 (Extractor):** ingesta IMAP + extracción + estandarización JSON (silver).
- **Agente 2 (Evaluador):** match score, fortalezas/brechas y ranking (gold).
- **Agente 3 (Asistente F4):** respuestas en lenguaje natural sobre silver/gold + simulador + costos + trazabilidad.
- **Administrador / responsable:** configura `.env`, define vacantes en `config/vacantes/`, edita prompts de `prompt/` y dispara las fases (`main.py`).
- **Sistemas externos:** Gmail (IMAP), API Gemini (Google), API Groq (proveedor OpenAI-compatible).

**C4. ¿Qué funciones quedaron fuera del alcance en esta versión (MVP) y por qué?**
- Envío automático de correos a candidatos: el sistema sólo redacta borradores; se deja fuera para evitar acciones no deseadas sin aprobación humana (seguridad).
- Integración con ATS/CRM pagos y bases en la nube: la persistencia es local (medallion) para privacidad y costo $0.
- RAG con base vectorial: las respuestas salen de silver/gold estructurados; no se requiere búsqueda sobre documentos en bruto para este volumen.
- Calibración con feedback humano del resultado real de contratación.
- Idiomas distintos al español y entrevistas autónomas: el sistema no decide la contratación.

---

## D. Requerimientos técnicos y no funcionales

**D1. Lenguajes, frameworks y bases de datos utilizados, con la versión de cada uno**
- **Python 3.12** (`.python-version` y `runtime.txt`).
- **FastAPI** >=0.141.1 (API del chatbot F4) · **uvicorn** >=0.52.4 (servidor local).
- **Streamlit** >=1.63.0 (dashboard F3, incluye pandas).
- **google-genai** >=2.22.0 (Gemini, Agente 1) · **openai** >=1.40 (cliente Groq/OpenAI-compatible, Agentes 2 y 3).
- **pdfplumber** >=0.11.10 y **python-docx** >=1.2.0 (extracción de PDF/DOCX).
- **python-dotenv** >=1.2.3 (`.env`) · **schedule** >=1.2.2 (lote programado).
- **Base de datos:** NO hay motor externo; persistencia en archivos JSON con arquitectura medallion bronze/silver/gold (`pyproject.toml` y README §7.2). Gestor de dependencias: **uv**.
- **Pruebas:** **pytest** (extra `dev`, `requirements-dev.txt`); 124 tests.
- **Despliegue:** Docker (`Dockerfile`, `Dockerfile.dashboard`, `docker-compose.yml`) y Vercel (serverless).

**D2. Requerimientos no funcionales y cómo los verificaron**
- **Tiempo de respuesta:** ranking F3 <3 s (criterio de listo, verificado 2026-09-06); lote F2 10 candidatos ~2 min (limitado por el free tier de Groq, que responde 429 y reintenta solo — log 2026-09-26). Verificado con AppTest de Streamlit y arranque real + `/_stcore/health`.
- **Disponibilidad:** F3/F4 funcionan offline con datos en archivos (0 dependencias externas); el chat responde 100% en código. En Vercel es serverless (cold start esperado en modo demo).
- **Seguridad:** credenciales sólo en `.env` (gitignored), escáner `tools/verificar_secretos.py` + hook pre-commit, login F4 con token Bearer de 12 h y `hmac.compare_digest`, IMAP con SSL y App Password.
- **Privacidad:** `data/` y `logs/` no se versionan (`.gitignore`/`.vercelignore`); F1 excluye foto, edad, género, dirección y estado civil; dashboard sólo red local (127.0.0.1).
- **Costo por consulta:** $0 en modo offline (chat code-first); con IA, estimado con tarifas editables en `config/tarifas.json` y bitácora `data/gold/costo/uso_chat.jsonl` (`core/costo.py`).

**D3. ¿Qué datos o documentos usa el sistema? ¿Qué licencia o permiso tienen?**
- **Entrada:** CVs en PDF/DOCX/TXT/MD enviados por correo a la cuenta de postulaciones (hasta ~30/día, README §2.1) y el cuerpo del correo como alternativa.
- **Regla de negocio:** requisitos por vacante en `config/vacantes/<SLUG>.json` (ej. `ANALISTA_DE_DATOS.json` con esenciales/opcionales, experiencia mínima y carreras).
- **Datos demo:** `data_demo/` con 30+ candidatos FICTICIOS (silver 33, gold 30 evaluaciones en 3 vacantes) generados por `tools/generar_datos_demo.py`; versionados en git.
- **Licencia/permiso:** los datos demo son generados por el equipo (no exponen datos de terceros); los CVs reales pertenecen a sus postulantes y sólo se usan para la preselección (no se publican ni se usan para entrenar modelos). El README no declara licencia de código (uso académico).

**D4. ¿Dónde se almacena la información y cómo se protege?**
- **Almacenamiento:** archivos JSON locales en `data/` con arquitectura medallion — bronze (originales por fecha/vacante), silver (CV estandarizado por `sha1(mensaje_id)`) y gold (evaluaciones + `ranking.json`), con escritura atómica (`tempfile` + `os.replace`) en `gold_store.py`.
- **Protección:** `data/`, `logs/` y `.env*` quedan fuera de git (`.gitignore`, `.vercelignore`); en tránsito se usa HTTPS/SSL (IMAP 993, APIs); en Vercel las variables son Environment Variables cifradas; acceso del dashboard restringido a red local y del chat a 127.0.0.1 + login opcional.
- **Respaldo:** la data personal es local (no hay backup en la nube, decisión de privacidad); `data_demo/` (ficticio) sí se respalda en git. La retención de bronze se purga con `main.py limpiar` (`RAWDATA_RETENCION_DIAS=90`).

**D5. Adjunta el diagrama de arquitectura general e indica cada componente**
Se adjunta el diagrama de la arquitectura construida como tal en la raíz del repo: **`diagrama_arquitectura_agente_rrhh.png`** (infografía de alta resolución en un solo lienzo, sin recortes) y su versión vectorial **`diagrama_arquitectura_agente_rrhh.svg`**. Flujo: Candidato → Gmail IMAP SSL → [Agente 1: extracción + Gemini] → bronze/ + silver/ (JSON medallion) → [Agente 2: evaluación con Groq + `reglas.py` (score 50/30/20, Alta/Media/Baja)] → gold/ + `ranking.json` → [F3 dashboard Streamlit] y [Agente 3 chatbot FastAPI + SPA (code-first, Vercel)]; con `core/` compartido (config, llm, costo, gold_store...), regla de negocio (`config/vacantes` + `prompt/` + tarifas) y despliegue local + Vercel (`data_demo`). En el diagrama: tarjetas = fases/agentes con barra de acento (azul F1 · verde F2 · naranja F3 · violeta F4), capas bronce/plata/oro = persistencia, bandas = core, regla de negocio y despliegue.

---

## E. Arquitectura multiagente (requisito eliminatorio)

**E1. Tabla de agentes**

| Agente | Rol y objetivo | Herramientas / APIs | Entradas | Salidas | Modelo de IA |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Agente 1 — Extractor** (`ingestion/`) | Ingerir postulaciones desde el correo y estandarizar el CV a JSON (silver), excluyendo atributos de sesgo. | Gmail IMAP (imaplib, SSL 993), pdfplumber, python-docx, API Gemini (google-genai), `prompt/extractor.md`. | Correo (asunto `POSTULACION - <vacante>`) + adjunto PDF/DOCX/TXT/MD o cuerpo. | Documento JSON silver (datos_contacto, datos_estructurados, control_sesgo) + estados de error. | **Gemini 3.5-flash** (`MODELO_GEMINI`, `GEMINI_API_KEY`) |
| **Agente 2 — Evaluador** (`evaluation/`) | Comparar el perfil contra los requisitos de la vacante y producir el desglose, fortalezas y brechas. | API Groq (SDK openai, endpoint compatible OpenAI), `config/vacantes/<SLUG>.json`, `prompt/evaluador.md`, `reglas.py`. | JSON silver (perfil estandarizado) + requisitos de la vacante (config). | Desglose 50/30/20, fortalezas, brechas, requisito esencial ausente, justificación; oro + `ranking.json`. | **openai/gpt-oss-120b** vía Groq (`MODELO_EVALUADOR` / `PROVEEDOR_EVALUADOR`) |
| **Agente 3 — Asistente de consultas F4** (`chatbot/`) | Responder consultas operativas de RRHH en lenguaje natural sobre silver/gold y orquestar simulación/costos/trazabilidad. | FastAPI + SPA, `dashboard/consultas.py` (lectura), `core/costo.py`, `prompt/chatbot.md`, IA opcional (`PROVEEDOR_CHAT`). | Pregunta del usuario + contexto ligero de sesión (vacante/candidato en foco). | Respuesta estructurada con bloques (tabla, tarjetas, listas), sugerencias, uso de tokens y costo. | Ninguno por defecto (offline 100% código, $0); opcional **openai/gpt-oss-120b**, **gemini-3.5-flash**, OpenRouter, Cerebras u Ollama |

**E2. ¿Qué patrón de orquestación usan y por qué?**
Patrón **SECUENCIAL con orquestador por etapa**: `main.py` dispara los pipelines (F1 `pipeline.py` → silver; F2 `pipeline_evaluacion.py` → gold; F3/F4 leen gold/silver de sólo lectura). Se eligió secuencial porque las fases dependen entre sí (primero se estandariza, luego se evalúa, luego se consulta) y porque permite idempotencia, reintentos acotados y trazabilidad por capa sin complejidad de grafo (los costos y errores se aíslan por etapa).

**E3. ¿Con qué framework o librería coordinan a los agentes? Indica la versión.**
Código propio (no LangGraph/CrewAI/AutoGen). La orquestación son pipelines explícitos en Python: `PipelineIngesta` (`src/agente_rrhh/ingestion/pipeline.py`) y `PipelineEvaluacion` (`src/agente_rrhh/evaluation/pipeline_evaluacion.py`), sobre la fachada `core/llm.py` y el CLI `main.py` (Python 3.12; punto de entrada único). Se usó código propio porque el flujo es determinista y de bajo costo; un framework de grafos habría añadido complejidad sin beneficio en este alcance.

**E4. ¿Cómo se comunican los agentes entre sí? ¿Qué información intercambian?**
Mediante mensajes estructurados JSON persistidos en disco (arquitectura medallion), como contrato entre etapas:
Agente 1 escribe `silver/candidatos/<sha1(mensaje_id)>.json`; Agente 2 lee silver y escribe `gold/evaluacion/<vacante>/<id>.json` + `ranking.json`; Agente 3 lee gold/silver (sólo lectura). Intercambian: perfil estandarizado, requisitos evaluados, desglose, score, fortalezas/brechas y metadatos de trazabilidad (`mensaje_id`, `id_candidato`, `uso_tokens`). No usan MCP/A2A: el JSON en disco garantiza idempotencia y auditoría.

**E5. ¿Qué memoria o estado compartido existe? ¿Qué recuerda cada agente?**
- **silver** = memoria estructurada de cada candidato (un JSON por `sha1(mensaje_id)`, idempotente).
- **gold** = memoria de evaluación por vacante (documento + `ranking.json`, escritura atómica).
- **Sesiones del chat** = estado ligero en memoria que recuerda la entidad en foco (vacante/candidato) para seguimientos ("¿su teléfono?"); guarda su historial de turnos y puede **persistirse opcionalmente** en `data/gold/chat_sesiones/` (`CHAT_PERSISTENCIA=1`); se resetea con "Nuevo chat" (`chatbot/sesion.py`).
- No hay base vectorial. El Agente 1 no guarda contexto entre llamadas (stateless); el pipeline recuerda lo ya procesado vía silver/gold (no reprocesa duplicados); el Agente 3 recuerda sólo la entidad en foco de la conversación.

**E6. ¿Qué decisiones toma cada agente por sí mismo y cuáles el orquestador o una persona?**
- **Agente 1** decide solo: reconocer encabezados del CV, unificar sinónimos y qué atributos excluir (sesgo).
- **Agente 2** decide solo: desglose parcial de cada bloque, fortalezas, brechas y requisito esencial ausente.
- **El orquestador/código** decide: los pesos 50/30/20, el score y la clasificación finales (`reglas.py`), la idempotencia (omitir ya evaluados), el ranking, los reintentos con backoff y el límite `max_candidatos` por vacante.
- **La persona** decide: qué vacantes y requisitos configurar, aprobar/enviar los borradores de correo, re-evaluar (`--re-evaluar`), purgar bronze y el login.
- **Caso de delegación:** cuando el usuario le pregunta al Agente 3 "¿quién pasa a fase técnica?", el asistente delega la lectura en la capa gold que produjo el Agente 2 (`dashboard/consultas.py` → ranking) y devuelve el resultado sin gastar tokens.

**E7. ¿Cómo evitan bucles infinitos, errores en cadena y acciones no deseadas?**
- **Bucles:** los lotes son finitos (sólo correos UNSEEN nuevos; idempotencia por `mensaje_id`); no hay auto-repetición de agentes.
- **Llamadas acotadas:** 1 llamada IA por candidato en F1 y 1 en F2; los fallos se guardan como "Pendiente: Reintento IA" / "Pendiente: Reintento Evaluación" y se reintentan en un lote posterior. F1 además reintenta **dentro del lote con backoff** (`core/reintentos.con_reintentos`, `IA_REINTENTOS`/`IA_ESPERA_REINTENTO`). El SDK de OpenAI reintenta automáticamente el 429 del free tier (retry 2, ver log).
- **Validación de salidas:** parseo JSON estricto tolerante (`core/prompts.parsear_json`) y score clampeado 0–100 en `reglas.py`; la IA no decide el puntaje final.
- **Chat:** `try/except` global que nunca tumba la app, fallback amigable/FAQ y límite `DEMO_CONSULTAS_IA=3` por conversación para la IA.
- **dry-run** (`--dry-run`) para probar sin gastar cuota ni escribir.

**E8. ¿Dónde interviene una persona (human-in-the-loop)?**
- Aprobar y ENVIAR los correos a candidatos: el sistema sólo redacta borradores de avance/rechazo.
- Definir vacantes y requisitos (`config/vacantes/`) y validar la regla 50/30/20.
- Re-evaluar candidatos (`--re-evaluar`) y limpiar bronze (`main.py limpiar`).
- Acceso: decidir si activa el login de F4 (`ADMIN_USUARIO`/`ADMIN_CLAVE`) y quién entra.
Acciones que requieren aprobación humana: todo contacto con el candidato y cualquier cambio definitivo de pesos (el simulador sólo explora; no modifica gold).

**E9. Evidencia obligatoria: traza o log real con dos o más agentes colaborando**
Log real del lote F2 (`logs/ingesta.log`, 2026-09-26) donde colaboraron Agente 1 → Agente 2 sobre la misma solicitud (vacante ANALISTA DE DATOS), con la entrada (correo `POSTULACION - ANALISTA DE DATOS` procesado por el Agente 1 en silver), la herramienta invocada (API Groq) y la salida final (evaluación + ranking):

```
[Agente 1] silver: 10 candidatos estandarizados listos (estado 'Listo para Evaluación').
[Agente 2] HTTP Request: POST https://api.groq.com/openai/v1/chat/completions "HTTP/1.1 200 OK"
[Agente 2] Evaluado 6d84e214fbbe0acb7a7805de06dbf482 (ANALISTA DE DATOS): score=58 -> Media
[Agente 2] ... score=82 -> Alta; 43 -> Baja; 77 -> Media; 90 -> Alta; 55 -> Media; 70 -> Media
[Agente 2] Resumen de evaluacion: {'Evaluado': 10}
[Agente 2] ranking.json recalculado (gold/evaluacion/ANALISTA_DE_DATOS/ranking.json).
```

Respuesta final que ve el usuario: ranking ordenado por match score en F3/F4 (ej. Ana María Gómez 95 Alta).

**Evidencia en línea:** el sistema expone `GET /api/traza` (público: https://agente-rrhh-five.vercel.app/api/traza) que devuelve la traza completa de un candidato a través de las etapas (correo → silver F1 → gold/ranking F2 → chat F4) y puede verse en la vista **"Traza del dato"** de la SPA.

**E10. ¿Por qué no podría resolverse con un solo agente o un solo prompt? ¿Qué se pierde sin cada agente?**
Cada etapa necesita un rol, formato y modelo distinto: extracción libre texto→JSON (Gemini, flexible, tolera redacciones distintas) vs. evaluación estructurada contra requisitos de negocio (Groq, JSON forzado) vs. consulta conversacional con datos verificados (code-first + IA opcional). Un solo agente/prompt haría un monolito imposible de ajustar por etapa, con contextos enormes (texto CV + requisitos + reglas + chat), sin trazabilidad por capa y con un único punto de fallo y de sesgo.
Si se elimina: Agente 1 → no hay CV estandarizado ni bloqueo de sesgo (silver desaparece); Agente 2 → no hay match score ni ranking (la extracción quedaría sin uso); Agente 3 → el usuario tendría que leer JSONs, perdiendo la consulta en lenguaje natural, simulador y costos.

---

## F. Modelos de IA, datos y costos

**F1. ¿Qué modelo usa cada agente, con qué proveedor y por qué?**
- **Agente 1:** Gemini 3.5-flash (Google) vía google-genai — bueno para extracción flexible texto→JSON con prompt editable; configurable con `MODELO_GEMINI`.
- **Agente 2:** openai/gpt-oss-120b vía Groq (API compatible OpenAI con `response_format=json`) — JSON determinista, 1 llamada por candidato, tier "Forever Free". Configurable con `MODELO_EVALUADOR`/`PROVEEDOR_EVALUADOR` (los `llama-3.3-*` no están habilitados en esta cuenta).
- **Agente 3:** sin LLM por defecto (offline $0); con `PROVEEDOR_CHAT` activo puede usar cualquiera de los modelos/proveedores soportados (Gemini, Groq, OpenRouter, Cerebras u Ollama) mediante `core/llm.py` y `Config.clave_ia`.
Razones: costo $0 (sólo free tiers), latencia (Groq es rápido), calidad por tarea y privacidad (no se entrena con los datos de los candidatos).

**F2. ¿El modelo se consume por API o se ejecuta localmente?**
Por API: Gemini (AI Studio) y Groq (api.groq.com/openai/v1). Ningún LLM se ejecuta localmente; el chat offline es code-first (cero tokens) y, si se desea IA, siempre se consume por API. Excepción opcional: el proveedor `ollama` permite un LLM local, pero no es el default. No hay hardware local que corra modelos grandes ni se requiere (el deploy Vercel corre sólo el chatbot offline con `data_demo`).

**F3. ¿Usan RAG?**
No. No hay recuperación sobre documentos en bruto ni base vectorial. El Agente 3 consulta directamente los JSON estructurados silver/gold (`ranking.json`, documento de evaluación, CV estandarizado). Comprobación de que las respuestas salen de esos datos: en modo offline los bloques (tablas/tarjetas) se construyen exclusivamente desde gold/silver (0 tokens) y se muestra "modo: offline" en cada respuesta; sólo la narrativa opcional usa el LLM con el contexto de esos mismos datos.

**F4. Costo estimado por 100 consultas y límites configurados**
- **Modo offline (default en Vercel):** 0 llamadas → **$0**.
- **Límites:** `DEMO_CONSULTAS_IA=3` consultas IA por conversación (chat); F2 hace 1 llamada por candidato (toggle `--re-evaluar` sólo si se pide) y `max_candidatos` limita el volumen por lote; `response_format=json` forzado; el free tier de Groq limita peticiones/minuto (429 + reintento automático del SDK).
- **Costo estimado:** usando `config/tarifas.json` (openai/gpt-oss-120b: $0.12 entrada / $0.30 salida por 1M tokens) y ~500 tokens de entrada + 200 de salida por consulta de chat, 100 consultas ≈ (500·0.12 + 200·0.30)/1e6 × 100 ≈ **$0.012**. F2: cada evaluación usó ~2.7k tokens (~$0.0007). Valores editables en `config/tarifas.json` y trazados en `data/gold/costo/uso_chat.jsonl` (resumen por lote F2 en `data/gold/costo/uso_fase2.jsonl`, visible en `GET /api/costos` como `fase2_lotes`).

**F5. ¿La clave de API es propia del equipo? ¿Dónde se guarda?**
Sí, son claves propias del equipo (`GEMINI_API_KEY` de AI Studio y `GROQ_API_KEY` de console.groq.com). Se guardan únicamente en el archivo `.env` local (excluido por `.gitignore` y `.vercelignore`) y, en el deploy Vercel, como Environment Variables cifradas. Nunca están en el código ni se loguean; el hook `tools/verificar_secretos.py` bloquea commits que las contengan. Sólo se indican los NOMBRES de las variables, sin valores.

---

## G. Despliegue en línea

**G1. Tipo de proyecto según las plantillas del curso**
☑ Chatbot web con IA (F4 FastAPI + SPA) y ☑ Agente en segundo plano (F1 ingesta programada IMAP + F2 evaluación por lotes). Incluye además un dashboard (F3) para red local.

**G2. Servicio o servidor donde está publicado y cómo se despliega**
Publicado en **Vercel** (plan Hobby gratis, `@vercel/python`): `vercel.json` con rutas a `api/index.py`, `runtime.txt=3.12`, `requirements.txt` (subset del chatbot), `data_demo/` versionado y `.vercelignore`. Pasos (README §8.3): subir el repo a GitHub → Import en Vercel → configurar Env Vars (`ADMIN_USUARIO`/`ADMIN_CLAVE`, opcional `DEMO_CONSULTAS_IA`; dejar `PROVEEDOR_CHAT` vacío para $0) → Deploy. **URL en línea:** https://agente-rrhh-five.vercel.app/. Local: `INICIAR.bat` / `iniciar.sh` → `main.py demo` (F3+F4) o `docker compose up` (F3 `:8501` + F4 `:8000`).

**G3. ¿El repositorio incluye Dockerfile, compose, .env.example y README con pasos?**
- **`.env.example`:** Sí (plantilla con placeholders, sin secretos).
- **README con pasos de ejecución:** Sí (README §7 Ejecución, §8 Deploy Vercel, §10 Entrega de un clic).
- **Dockerfile / docker-compose:** Sí. `Dockerfile` (chatbot F4 offline $0, `python:3.12-slim`), `Dockerfile.dashboard` (Streamlit F3 con `requirements-full.txt`) y `docker-compose.yml` (servicios `chatbot` en `:8000` y `dashboard` en `:8501`), con `.dockerignore` que excluye `.env*`, `data/`, `logs/`, `.venv/`, `.git/` y entregables.

**G4. Lista de variables de entorno necesarias (solo nombres) y para qué sirve cada una**
`EMAIL` (usuario IMAP Gmail), `API_EMAIL` / `PASSWORD` (App Password 16 caracteres o respaldo), `IMAP_TIMEOUT` (timeout conecta), `ASUNTO` (prefijo de postulaciones), `DIAS_ATRAS` (ventana de búsqueda), `HORA_INGESTA` (lote programado), `RAWDATA_RETENCION_DIAS` (purga bronze), `GEMINI_API_KEY` + `MODELO_GEMINI` (Agente 1), `GROQ_API_KEY` + `PROVEEDOR_EVALUADOR` + `MODELO_EVALUADOR` (Agente 2), `PROVEEDOR_CHAT` + `MODELO_CHAT` (narrativa opcional del chat; vacío = offline $0), `OPENROUTER_API_KEY` / `CEREBRAS_API_KEY` / `OLLAMA_BASE_URL` (proveedores alternativos del chat), `DEMO_CONSULTAS_IA` (límite IA por conversación), `ADMIN_USUARIO` + `ADMIN_CLAVE` (login F4), `DATA_DIR` (raíz medallion; `data_demo` en Vercel), `PROMPT_EXTRACTOR` + `PROMPT_EVALUADOR` (prompts), `RUTA_VACANTES` (requisitos), `RUTA_TARIFAS` (costos), `RUTA_HABILIDADES` (diccionario de niveles), `IA_REINTENTOS` + `IA_ESPERA_REINTENTO` (backoff F1), `CHAT_PERSISTENCIA` (historial de sesiones en disco). Detalle de cada una en `.env.example`.

**G5. Dirección del endpoint de salud y resultado de consultarlo**
- **Chatbot F4 (en línea / local):** `GET /api/health` → HTTP 200
  ```json
  {"ok": true, "modo": "groq", "data_dir": "data_demo", "proveedor_chat": "groq", "modelo_chat": "openai/gpt-oss-120b", "limite_ia_demo": 3, "login": "desactivado"}
  ```
  (en https://agente-rrhh-five.vercel.app/api/health; con `PROVEEDOR_CHAT` vacío devuelve `"modo": "offline"`).
- **Dashboard F3 (local, red local):** `GET /_stcore/health` → `"ok"` (verificado 2026-09-06).

**G6. Usuario y datos de prueba para que el docente use el sistema sin registrarse**
No requiere registro. El login de F4 está **desactivado** en el deploy (no hay `ADMIN_USUARIO`/`ADMIN_CLAVE` configurados) y se entra directo con los datos ficticios de `data_demo/`: vacante "ANALISTA DE DATOS" con ranking (Ana María Gómez 95 Alta, Diego Salazar 90 Alta, Carla Vega 84 Alta...), "DESARROLLADOR BACKEND" y "EJECUTIVO COMERCIAL". Consultas de prueba sugeridas en el chat: "Ranking de ANALISTA DE DATOS", "¿Quiénes pasan a fase técnica?", "Fortalezas y brechas de Ana Gomez", "¿Cuánto hemos gastado en IA?", "Compara a Ana con Carla". El login puede activarse con `ADMIN_USUARIO`/`ADMIN_CLAVE` si se prefiere (reportar el usuario de prueba, sin contraseñas reales).

**G7. Tiempo promedio de respuesta medido en línea y cantidad de usuarios simultáneos que probaron**
- **En línea:** el chatbot F4 en Vercel responde en el orden de pocos segundos (incluye cold start serverless); el dashboard F3 local responde en <3 s por consulta (criterio de listo) y el chat offline en milisegundos (0 tokens).
- **Usuarios simultáneos probados:** 1–2 (equipo). *(El equipo puede ampliar esta medición con carga concurrente antes de la sustentación.)*

---

## H. Seguridad y ética

**H1. ¿Qué datos personales o sensibles procesa y cómo cumplen con protección de datos?**
Procesa nombre, teléfono, correo e historial laboral/académico de postulantes (silver/gold). Cumplimiento: uso exclusivo para la preselección (no se comparte ni se usa para entrenar modelos); `data/` y `logs/` no se versionan (`.gitignore`/`.vercelignore`); el Agente 1 excluye deliberadamente foto, edad, género, dirección y estado civil (`control_sesgo`); el dashboard sólo se sirve en red local; el chat puede exigir login; la demo en línea usa SÓLO datos ficticios (`data_demo`).

**H2. ¿Qué medidas tomaron contra prompt injection y alucinaciones?**
- Los prompts instruyen a no inventar datos y a devolver sólo lo presente en el perfil.
- La IA no decide el resultado final: respuesta validada como JSON (`core/prompts.parsear_json`) y el score/clasificación se recalculan en código (`reglas.py`), de modo que una respuesta "adversaria" no altera el veredicto.
- En el chat offline las respuestas salen de silver/gold verificados (0 tokens); si la IA no está disponible se contesta offline con aviso.
- El texto del CV del candidato se incorpora como dato ya estructurado JSON al evaluador (menor superficie de inyección). Limitación honesta: no existe un sanitizador formal anti-prompt-injection sobre el texto crudo del CV; se mitiga por diseño (perfil estructurado).

**H3. ¿Qué acciones no puede ejecutar el sistema sin autorización?**
No envía correos (sólo redacta borradores que una persona aprueba y envía), no realiza pagos ni llamadas de pago, no borra datos (la purga de bronze es un comando explícito manual: `main.py limpiar`, y los borrados no tocan silver/gold), no contacta postulantes y no modifica los pesos definitivos (el simulador es de exploración). Con login activo, no entrega datos de `/api/*` sin token válido (401).

**H4. ¿Los agentes registran sus acciones para auditoría? ¿Dónde se pueden ver?**
Sí: cada lote escribe en `logs/ingesta.log` el detalle asunto → remitente → estado → (score para F2); cada llamada IA del chat se registra en `data/gold/costo/uso_chat.jsonl` (fecha, fase, proveedor, modelo, tokens, costo); cada evaluación gold guarda `fecha_evaluacion`, modelo, proveedor y `uso_tokens`; existe un agregado por lote F2 en `data/gold/costo/uso_fase2.jsonl`; y el historial de cambios del código queda en los commits del repositorio (`git log`). El chatbot expone además `GET /api/traza` para auditar el recorrido de un candidato por las etapas y la vista de costos/pipeline en la SPA.

**H5. Riesgos éticos del proyecto (sesgos, uso indebido, impacto en el empleo) y cómo los mitigan**
- **Sesgo de la IA:** mitigado porque la IA propone pero no decide el puntaje (reglas 50/30/20 en código), se excluyen atributos sensibles desde F1 y el desglose queda visible y auditable en cada ficha.
- **Uso indebido:** sin envío automático (borradores), puertos restringidos a local, login opcional, datos ficticios en línea.
- **Impacto en el empleo:** el sistema preselecciona; la decisión final (entrevista y contratación) sigue siendo humana, y el rol del reclutador se libera de tareas repetitivas.
- **Alucinaciones/errores:** validación de JSON, datos verificados y estados auditables.

---

## I. Pruebas y evidencias

**I1. Matriz de pruebas (mínimo 6 casos)**

| Entrada | Resultado esperado | Resultado real | Agente que intervino | ¿Pasó? |
| :--- | :--- | :--- | :--- | :--- |
| Correo `POSTULACION - ANALISTA DE DATOS` + PDF legible | Silver "Listo para Evaluación" con `datos_estructurados` | OK (lote real 2026-09-06) | Agente 1 | Sí |
| PDF de imagen/corrupto | "Error: Archivo Ilegible" sin llamar a la IA | OK | Agente 1 | Sí |
| Adjunto `.exe` | "Error: Formato No Permitido" | OK | Agente 1 | Sí |
| `main.py evaluar --vacante "ANALISTA DE DATOS"` (10 candidatos) | gold + `ranking.json` con scores 0–100 y clase | OK (scores 43/55/58/70/77/82/90... 2026-09-26) | Agente 2 | Sí |
| `main.py evaluar` sin `--re-evaluar` | Omitir ya evaluados (idempotencia, 0 llamadas) | OK | Agente 2 | Sí |
| Consulta ranking en dashboard F3 | Respuesta <3 s y `/_stcore/health` = ok | OK (2026-09-06, 2026-10-10) | Datos gold (F2) + Streamlit | Sí |
| Chat F4 offline: "Ranking de ANALISTA DE DATOS" | Tabla con datos verificados y `uso=None` ($0) | OK (TestClient + arranque real) | Agente 3 | Sí |
| `GET /api/ranking` sin token (login activo) | HTTP 401 | OK | Agente 3 | Sí |
| `POST /api/simular` con pesos alternativos | Re-ranking con clamp 0–100 y umbrales 80/50, sin IA | OK | Agente 3 | Sí |
| `main.py --dry-run` (F1) y `evaluar --dry-run` (F2) | 0 llamadas IA, no escribe silver/gold | OK | Agentes 1 y 2 | Sí |
| Suite `pytest` (124 casos sobre `data_demo`) | Todos pasan | OK → `124 passed` | F1–F4 + core + tools | Sí |
| `GET /api/traza` (en línea) | Traza completa del candidato por etapa | OK (HTTP 200) | Agente 3 + F1/F2 | Sí |

**I2. Métricas obtenidas y método de medición**
- **% tareas resueltas correctamente:** F1 lote real 1/1 (extracción OK); F2 10/10 evaluados (100%), con 429 del free tier superado por reintento automático; chat: 10/10 utilidades responden en TestClient (ranking, candidato, seguimiento, comparador, brechas, origen, borrador, costos, simulador, fallback/FAQ); suite `pytest`: 124/124.
- **Tiempo:** F3 ranking <3 s (AppTest + health); lote F2 10 candidatos ~2 min (limitado por Groq).
- **Costo:** offline $0; F2 ejemplo 2.691 tokens/evaluación (prompt 1386 + completado 1305); costos del chat en `uso_chat.jsonl`.
- **Tasa de error:** sin fallos no recuperados tras los reintentos; estados de error quedan auditados.
- **Método:** logs (`ingesta.log`), AppTest de Streamlit, TestClient de FastAPI, health checks, suite `pytest` y revisión del JSON de silver/gold.

**I3. Un caso de falla y cómo lo corrigieron**
- **Caso 1:** el overlay de login de la SPA no se ocultaba tras autenticarse (selector `.login-screen[hidden]` roto). Se corrigió con el fix de CSS del checkpoint 2026-09-20.
- **Caso 2:** el free tier de Groq respondía HTTP 429 durante el lote F2. Corrección: se apoya en el reintento automático del SDK (retry 1 de 2) y cualquier fallo persistente pasa a estado "Pendiente: Reintento Evaluación" en vez de perder el candidato (no gasta cuota extra).
- **Caso 3:** `gemini-2.5-flash` quedó obsoleto/saturado para claves nuevas. Corrección: migración a `gemini-3.5-flash` (`MODELO_GEMINI`) documentada en `PENDIENTES.md` F1.

**I4. Capturas de pantalla de la solución funcionando en la URL pública**
PENDIENTE DE ENTREGA: incluir capturas del chatbot F4 (y del dashboard F3 local) corriendo en la URL pública desplegada (A5), más la respuesta de `/api/health` en el navegador.

---

## J. Gestión del proyecto

**J1. Metodología de trabajo y cronograma real**
Metodología Scrum visual con bitácora en `PENDIENTES.md` (backlog → en progreso → hecho, con prioridades y definición de listo por fase). Cronograma real (checkpoints fechados en `PENDIENTES.md`):
2026-09-05 F1 implementada (IMAP, extracción, Gemini, silver/bronze) · 2026-09-06 F1 end-to-end real, F2 (Groq, reglas 50/30/20, gold+ranking) y F3 dashboard · 2026-09-07 F4 chatbot (motor code-first $0) · 2026-09-08 deploy Vercel configurado (`data_demo` 30+) · 2026-09-20 login F4, datos unificados, guard anti-secretos · 2026-09-26 entrega de un clic (`INICIAR.bat`/`iniciar.sh`, `main.py demo`) y F2 demostrable en vivo (`--re-evaluar`) · 2026-10-10 deploy en línea, Docker F3+F4 y suite de pruebas · 2026-10-11 backlog F1/F2/F4 cerrado (reportes, reintentos con backoff, `max_candidatos`, diccionario de habilidades, agregador de tokens, multi-proveedor IA, historial y trazabilidad) y `pytest` → 124 tests.

**J2. ¿Qué hizo cada integrante? Enlaza sus aportes en el repositorio**
PENDIENTE DE EQUIPO: asignar a cada integrante los módulos y commits (`git log`: `44c7604` F1, `df99580` F2, `c668aa6` F4, `dd1bc28`/`c039bd0` documentación, `73ab8ca` prompt maestro + anti-secretos, `8513bf3` scripts de inicio, `fc71719` cierre backlog + tests) en https://github.com/KCIRE17/Agente_RRHH/commits/main.

**J3. ¿Qué aprendieron y qué mejorarían en una siguiente versión?**
Aprendizajes: arquitectura medallion, agentes con modelos distintos y límites free tier, idempotencia y reintentos, mitigación de sesgos (la IA propone, el código decide), despliegue serverless (Vercel), contenedores (Docker) y guard anti-secretos.
Mejoras **implementadas ya en el MVP final**: persistencia e historial de sesiones del chat, agregador de tokens por lote, soporte de más proveedores (OpenRouter/Cerebras/Ollama), lote "desde la última ejecución", diccionario de habilidades por nivel y endpoint de trazabilidad (`/api/traza`).
Mejoras para una futura versión: RAG con base vectorial al crecer el volumen del corpus y calibración con feedback humano del resultado real de contratación.

---

## K. Declaración final

- [ ] **K1.** Declaro que las respuestas coinciden con las de mi equipo y que el sistema se encuentra en línea y funcionando en la URL indicada.
  *(La URL de A5 ya está desplegada y responde; marcar al confirmar.)*
- [ ] **K2.** Declaro que no incluí claves, contraseñas ni datos personales reales en el repositorio.
  *(El repositorio lo cumple: `.env` fuera de git, escáner anti-secretos activo y `data_demo` ficticio.)*
- [ ] **K3.** Declaro que el sistema usa agentes que colaboran entre sí y que puedo explicar su funcionamiento en una sustentación oral.
  *(El sistema cumple: 3 agentes colaboran vía silver/gold; README §5/§8 y `PENDIENTES.md` §E.)*
