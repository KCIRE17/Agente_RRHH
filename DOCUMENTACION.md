# Agente RRHH — Informe del Proyecto

**Sistema de automatización de la preselección de talento: ingesta, evaluación,
visualización y consulta de candidatos (F1–F4)**

Documento integral del proyecto, más allá de lo técnico: planteamiento,
objetivos, metodología, decisiones de diseño y resultados. Complementa a
`README.md` (especificación técnica) y `PENDIENTES.md` (bitácora Scrum).

---

## 1. Resumen ejecutivo

El **Agente RRHH** es un sistema que automatiza la **primera etapa del proceso
de selección** de una organización: recibe las postulaciones de candidatos por
correo, estandariza la información de sus hojas de vida, la evalúa de manera
**objetiva y reproducible** frente a los requisitos de cada vacante, y pone los
resultados a disposición del área de talento a través de un **tablero de
control** y un **asistente conversacional**.

El sistema está organizado en **cuatro fases**:

| Fase | Nombre | Responsable | Estado |
| :--- | :--- | :--- | :--- |
| **F1** | Ingesta y Extracción de Candidaturas | Agente 1 (Gemini) | Implementada |
| **F2** | Evaluación y Match Score | Agente 2 (Groq) | Implementada |
| **F3** | Dashboard y Visualización | Panel Streamlit | Implementada |
| **F4** | Chatbot de consultas de RRHH | Asistente web (FastAPI) | Implementada |

Principios que lo atraviesan: **costo operativo $0** (herramientas libres y
*tiers gratuitos* de IA), **persistencia local** en arquitectura medallion,
**reproducibilidad del puntaje** (los pesos y umbrales se calculan en código,
no en el modelo) y **mitigación de sesgos** (los atributos personales no
pertinentes se descartan desde la ingesta).

---

## 2. Introducción

### 2.1 Contexto

En la preselección tradicional, un analista de talento humano debe: abrir cada
correo de postulación, leer la hoja de vida, identificar manualmente si el
perfil cumple los requisitos de la vacante y archivar la evidencia. El proceso
repite esta rutina por cada remitente y por cada vacante, sin un criterio único,
sin trazabilidad del motivo de cada decisión y con un alto consumo de tiempo en
tareas de bajo valor agregado.

A esto se suman dos riesgos:

- **Subjetividad**: dos analistas pueden puntuar al mismo candidato de forma
  distinta según su impresión personal, sin un estándar verificable.
- **Sesgo inconsciente**: atributos como el género, la edad, la fotografía o la
  procedencia pueden influir (aun sin intención) en la decisión, penalizando a
  candidatos con perfiles técnicamente equivalentes.

### 2.2 Problemática

- La información de las hojas de vida llega **desestructurada** (cada CV usa
  encabezados distintos: "Experiencia", "Trayectoria", "Historial laboral").
- No existe un **criterio de evaluación común** entre vacantes ni entre
  analistas; el puntaje final es difícil de explicar y de defender.
- Las decisiones de "quién pasa a fase técnica" **no quedan documentadas**,
  lo que dificulta la revisión y la mejora continua.
- El **ranking** de candidatos se elabora manualmente y queda disperso en hojas
  de cálculo, correos o memorias no auditables.

### 2.3 Justificación

Este proyecto propone resolver la problemática con un sistema local y de bajo
costo que:

1. **Centraliza** la llegada de postulaciones (buzón IMAP dedicado).
2. **Estandariza** con IA la lectura de los CV (extracción a JSON uniforme) sin
   depender de la redacción particular de cada documento.
3. **Evalúa con pesos fijos y auditables** (Habilidades 50 % / Experiencia
   30 % / Formación 20 %) calculados en código, de modo que el puntaje sea el
   mismo sin importar quién ni cuándo se ejecute.
4. **Descarta deliberadamente** los atributos propensos a sesgo desde la fase 1.
5. **Visualiza** el ranking y **responde consultas** al área de RRHH en lenguaje
   natural, reduciendo el tiempo de decisión de horas a minutos.

Todo ello **sin depender de servicios de pago ni de infraestructura en la
nube**: la operación completa corre en un equipo local con la persistencia en
archivos, lo que también protege la confidencialidad de los datos personales.

---

## 3. Marco conceptual

| Término | Definición en este proyecto |
| :--- | :--- |
| **Candidato / postulante** | Persona que envía su hoja de vida por correo para una vacante. |
| **Hoja de vida (CV)** | Documento de postulación (PDF, DOCX, TXT, MD) o cuerpo del correo. |
| **Estandarización JSON** | Conversión del CV libre a un formato uniforme (habilidades, experiencia, formación, certificaciones) mediante IA. |
| **Match score** | Puntaje de compatibilidad 0–100 entre el perfil del candidato y los requisitos de la vacante. |
| **Clasificación** | Nivel derivado del puntaje: **Alta** (≥ 80), **Media** (50–79), **Baja** (< 50). |
| **Requisito esencial ausente** | Campo obligatorio de la vacante sin evidencia en el CV (puntaje 0 en ese bloque y alerta). |
| **Fortalezas / brechas** | Aspectos en los que el candidato destaca / requisitos que le faltan. |
| **Fase técnica** | Etapa posterior del proceso de selección a la que se recomienda pasar a los candidatos de compatibilidad Alta. |
| **Extracción con LLM** | Uso de un modelo de lenguaje (Gemini) para leer texto no estructurado y producir datos estructurados. |
| **Arquitectura medallion** | Organización de los datos en capas de calidad creciente: **bronze** (crudos), **silver** (estandarizados), **gold** (evaluados y listos para consumo). |
| **Idempotencia** | Capacidad de procesar un mismo correo varias veces sin duplicar candidatos (identidad por `mensaje_id`). |
| **Tokens** | Unidad de consumo de las APIs de IA; base para el cálculo de costos. |

---

## 4. Objetivos, misión y visión

### 4.1 Misión

Automatizar la preselección de talento para que el área de recursos humanos
dedique su tiempo a las decisiones y las personas, no a la lectura manual de
hojas de vida.

### 4.2 Visión

Convertirse en el primer filtro confiable y auditable de la organización:
un sistema que recibe cada postulación, la evalúa con un criterio único,
transparente y sin sesgos, y acerca al analista el ranking de los perfiles más
compatibles en segundos y con costo $0.

### 4.3 Objetivo general

Implementar un sistema integral de preselección que reciba, estandarice,
evalúe, visualice y consulte las postulaciones de candidatos frente a los
requisitos de cada vacante, garantizando puntajes reproducibles, trazabilidad
de las decisiones y cero costo operativo.

### 4.4 Objetivos específicos

**F1 — Ingesta y Extracción**

- Obtener automáticamente las postulaciones del buzón de correo dedicado
  (hasta ~30 CVs diarios) mediante IMAP, sin marcar los correos como leídos en
  la inspección.
- Extraer el texto de CV en PDF, DOCX, TXT y MD (o del cuerpo del correo),
  detectando archivos corruptos o imágenes escaneadas para preservar la cuota
  de IA.
- Estandarizar el perfil con el Agente Extractor (Gemini) a un JSON uniforme,
  normalizando sinónimos de encabezados y **excluyendo** atributos de sesgo
  (foto, edad, género, dirección, estado civil).
- Persistir la evidencia en **bronze** (original) y el JSON en **silver**
  (idempotente por `message-id`), con una matriz de excepciones clara para
  archivos ilegibles, formatos no permitidos y reintentos de IA.

**F2 — Evaluación y Match Score**

- Evaluar cada perfil contra los requisitos de la vacante con ponderación fija
  **50/30/20** (habilidades / experiencia / formación).
- Calcular el **puntaje final y la clasificación en código** (reglas
  deterministas), sin confiar ciegamente en el puntaje propuesto por el modelo.
- Generar el reporte de **fortalezas, brechas y requisitos esenciales ausentes**
  por candidato y el **ranking** ordenado de la vacante en la capa **gold**.

**F3 — Dashboard**

- Proveer una interfaz local e interactiva en **lenguaje de RRHH** (ranking por
  vacante, ficha del postulante, resumen de postulaciones y metodología) con
  respuesta a una consulta de ranking en menos de 3 segundos sobre archivos
  locales.

**F4 — Chatbot de consultas**

- Responder consultas operativas del encargado de talento en lenguaje natural
  (ranking, postulantes, fase técnica, brechas, comparaciones, origen,
  borradores, pipeline y costos).
- Mantener la consulta **100 % en código por defecto (costo $0)**; la IA
  opcional solo enriquece la narrativa si se configura explícitamente.

### 4.5 Público objetivo y casos de uso

**Usuarios**

- Encargado(a) de talento humano / analista de selección.

**Casos de uso principales**

| Caso | Pregunta típica | Respuesta del sistema |
| :--- | :--- | :--- |
| Priorizar postulantes | "¿Quiénes pasan a fase técnica?" | Lista de candidatos con compatibilidad Alta (con teléfono y correo). |
| Revisar un perfil | "Fortalezas y brechas de Ana Gómez" | Ficha con puntaje, nivel, fortalezas y aspectos por reforzar. |
| Comparar perfiles | "Compara a Ana con Luis" | Tabla lado a lado por criterio (score, bloques, habilidades, años). |
| Monitorear el flujo | "¿Cuántas postulaciones tenemos?" | Resumen por estado (Listo, Evaluado, Errores, Reintentos) y por vacante. |
| Ajustar criterios | "Simulador de pesos" | Re-pesaje 50/30/20 alternativo sobre el desglose guardado, sin IA. |
| Auditar el gasto | "¿Cuánto hemos gastado en IA?" | Suma de tokens por fase y costo estimado; $0 en modo offline. |

---

## 5. Metodología y desarrollo

El proyecto se desarrolló en **fases incrementales** (metodología Scrum,
bitácora en `PENDIENTES.md`). Cada fase se verificó con pruebas automatizadas
(compilación, `--dry-run`, `TestClient`/`AppTest` y *health checks*) antes de
pasar a la siguiente.

### 5.1 Flujo general de datos

```
[ Buzón de correo (IMAP) ]
        │  F1 · filtro por asunto, fecha y UNSEEN
        ▼
[ Extracción de texto (PDF/DOCX/TXT/MD) ] ──▶ bronze (originales, idempotente)
        ▼
[ Agente Extractor · Gemini ] ──▶ silver (JSON estandarizado por candidato)
        │                            estado: "Listo para Evaluación"
        ▼
[ Agente Evaluador · Groq ]  ──▶ desglose propuesto por la IA
        ▼
[ reglas.py ]  ──▶ match_score y clasificación calculados en código
        ▼
[ gold (evaluación por candidato + ranking.json) ]
        │
        ├──▶ F3 · Dashboard Streamlit (rankings, fichas, metodología)
        └──▶ F4 · Chatbot web (consultas en lenguaje natural, costo $0)
```

### 5.2 Fase 1 — Ingesta y Extracción (Agente 1)

- **Conexión**: IMAP SSL a `imap.gmail.com:993` con contraseña de aplicación;
  búsqueda de no leídos filtrada por **asunto y fecha en el servidor**
  (`BODY.PEEK[]`, no marca correos como leídos).
- **Sintaxis de entrada**: asunto `POSTULACION - <Nombre del Puesto>`; a partir
  de él se deriva la `vacante_id`.
- **Extracción**: `pdfplumber` (PDF), `python-docx` (DOCX) y lectura de texto
  simple (TXT/MD); fallback al cuerpo del correo. PDFs escaneados/corruptos se
  detectan y **no** se envían a la IA.
- **Sanitización**: normalización UTF-8, sin tildes y sin espacios redundantes.
- **Estandarización**: el texto saneado va al modelo Gemini (prompt editable en
  `prompt/extractor.md`) que unifica encabezados y produce el JSON. La salida
  documenta la **exclusión deliberada** de atributos de sesgo.
- **Persistencia**: bronze (copia del original) + silver
  (`<sha1(mensaje_id)>.json`) con idempotencia por `message-id`.
- **Matriz de excepciones**: `Error: Archivo Ilegible`, `Error: Formato No
  Permitido`, `Pendiente: Reintento IA` (pérdida de conexión conserva el texto
  para el siguiente lote) y `Listo para Evaluación`.

### 5.3 Fase 2 — Evaluación y Match Score (Agente 2)

- **Requisitos por vacante** en `config/vacantes/<SLUG>.json` (regla de negocio
  versionable): habilidades esenciales/opcionales, experiencia mínima en años y
  carreras de formación aceptadas.
- **Una sola llamada de IA por candidato**: el prompt lleva perfil + requisitos;
  el modelo propone un `desglose_puntos` por bloque.
- **Cálculo en código** (`evaluation/reglas.py`): los pesos 50/30/20 se aplican
  sobre los parciales propuestos; el puntaje se clampa a 0–100 y la
  clasificación se deriva de umbrales estables (80/50).
- **Idempotencia**: un candidato ya evaluado se omite en lotes posteriores
  (lo que también controla el gasto de tokens).
- **Salida**: documento gold por candidato (score, desglose, fortalezas,
  brechas, requisito esencial ausente, uso de tokens y snapshot de requisitos)
  + `ranking.json` para el panel.

### 5.4 Fase 3 — Dashboard (Streamlit)

Panel local que **solo lee** gold/silver (no llama a la IA ni escribe).
Vistas: **Ranking de postulantes**, **Postulante** (ficha con explicación del
cálculo), **Postulaciones** (resumen por situación/y vacante) y **Metodología**
(proceso en lenguaje de talento). Incluye la sugerencia de RRHH por nivel:
Alta → "Pase a fase técnica", Media → "Revisión manual", Baja → "No avanza".
Lecturas cacheadas 30 s con botón de actualización.

### 5.5 Fase 4 — Chatbot de consultas (FastAPI + SPA)

Asistente web responsivo que responde en lenguaje natural consultas sobre los
datos ya evaluados. **Motor code-first**: la clasificación de intención y los
elementos visuales (tablas, tarjetas, listas) se generan en código sobre
silver/gold, **sin gastar tokens**. La IA es un refuerzo narrativo **opcional**
(activado solo con `PROVEEDOR_CHAT` en `.env`); si falla, el chat responde igual
con los datos verificados y avisa.

Utilidades: ranking por vacante, ficha de candidato (con seguimiento de
entidad en foco, p. ej. "¿su teléfono?"), recomendación de fase técnica,
pipeline por estado/vacante, brechas de mercado, comparador de dos candidatos,
origen por dominio del correo, borradores de comunicación (avance/rechazo),
simulador de pesos y resumen de costos. Servidor **solo en `127.0.0.1`**.

---

## 6. Reglas de negocio y métricas

### 6.1 Fórmula de compatibilidad

```
match_score = Habilidades × 0.50 + Experiencia × 0.30 + Formación × 0.20
```

- Los parciales los propone la IA; **la composición y los umbrales son
  deterministas** (se validan y clamps se aplican en código).
- Un requisito esencial sin evidencia penaliza su bloque con puntaje 0 y
  genera una alerta (`requisito_esencial_ausente`).

### 6.2 Clasificación

| Puntaje | Nivel | Sugerencia de RRHH |
| :--- | :--- | :--- |
| 80–100 | **Alta** | Pase a fase técnica |
| 50–79 | **Media** | Revisión manual |
| < 50 | **Baja** | No avanza |

### 6.3 Idempotencia y control de gasto

- F1 identifica candidatos por `mensaje_id` (`sha1` del documento silver): el
  mismo correo procesado dos veces **nunca se duplica**.
- F2 evalúa cada candidato una única vez; los evaluados se omiten en lotes
  siguientes. **1 llamada de IA por candidato** en F2; **0 llamadas por defecto**
  en F4.

---

## 7. Decisiones tecnológicas y alternativas evaluadas

Esta sección documenta las **alternativas estudiadas** y las razones de la
decisión final, en el espíritu de un trabajo de investigación aplicada.

### 7.1 Persistencia de datos: MongoDB vs. almacenamiento local

Durante el diseño se evaluó **MongoDB** como base de documentos para los
candidatos. Se descartó en favor de la **arquitectura medallion local basada en
archivos JSON**.

| Criterio | MongoDB | JSON local (bronze/silver/gold) |
| :--- | :--- | :--- |
| Infraestructura | Requiere servidor (local o Atlas nube) | Ninguna (carpetas en disco) |
| Costo operativo | Gratis solo hasta cierta escala/free tier; costos a partir de volumen o gestión del cluster | $0 |
| Privacidad | Datos personales viajan a un servicio externo o requieren configuración de red y anonimización | Datos nunca salen del equipo (`data/` gitignored) |
| Portabilidad/backup | Requiere estrategia de respaldo del motor de BD | Copiar la carpeta basta; auditable archivo por archivo |
| Curva y mantenimiento | Drivers, esquema, índices, backup, versionado | Baja; sin migraciones |
| Consultas cruzadas | Potente (agregaciones, índices) | Manual (lectura de archivos) |
| Escala | Millones de documentos | Sobrada para ~30 CVs/día |

**Otras alternativas consideradas**

- **SQLite**: incorporado, SQL real, $0 y portable. Se consideró como opcional
  futura si el volumen crece o se requieren consultas cruzadas; la estructura
  fija con migraciones añade fricción frente a la flexibilidad del JSON por
  candidato del MVP.
- **PostgreSQL**: muy robusto (índices, multi-usuario, concurrencia), pero
  implica un servicio dedicado; sobre-dimensionado para un MVP local de una
  organización pequeña.

**Decisión**: capas bronze/silver/gold en archivos JSON locales, por **costo $0,
privacidad, simplicidad y volumen acotado**. Queda documentado que, si el
proyecto crece en volumen o en usuarios concurrentes, el siguiente paso natural
es `SQLite` (migración directa de los documentos JSON) y recién *entonces*
evaluar `PostgreSQL`/`MongoDB` con servicios gestionados. La separación de
capas (crudo → estandarizado → evaluado) es independiente del medio físico de
persistencia, por lo que la arquitectura no bloquea esa evolución.

### 7.2 Modelos de IA por fase

| Proveedor | Uso actual | Tier | Motivo |
| :--- | :--- | :--- | :--- |
| **Gemini** (Google) | F1 · Agente Extractor | Gratuito (API Key) | Excelente para transformar texto libre en JSON estructurado y afinar encabezados de CV ("Trayectoria" → `experiencia_laboral`). |
| **Groq** (API compatible OpenAI) | F2 · Agente Evaluador · F4 narrativa opcional | "Forever Free" | Baja latencia y cuota gratuita estable; disponible `openai/gpt-oss-120b`, `qwen/*` y `groq/*` (se consultan con `GET /openai/v1/models`). |
| **OpenRouter / Cerebras / Ollama** | No activos | — | Alternativas estudiadas: agregador multi-modelo y ejecución local (Ollama). La fachada `core/llm.py` es el **único punto de contacto con APIs**, de modo que sumar estos proveedores no toca el resto del sistema. |

**Principio aplicado**: cada fase usa el modelo más adecuado a su tarea; el
cálculo de reglas de negocio (pesos, umbrales) nunca queda a cargo del modelo,
garantizando reproducibilidad.

### 7.3 Interfaces y frontend

| Opción | Evaluación | Resultado |
| :--- | :--- | :--- |
| **Streamlit** | Ideal para dashboards interactivos locales en minutos | Elegido para **F3** (vistas de ranking, ficha, resumen, metodología) |
| **FastAPI + SPA (HTML/CSS/JS)** | API REST + frontend ligero, control total, cero dependencias en el navegador, fácil de servir solo en `127.0.0.1` | Elegido para **F4** (chat conversacional responsivo + paneles Simulador/Brechas/Costos) |

Ambas opciones son **gratuitas y locales**; se utilizan para propósitos
complementarios.

### 7.4 Stack de soporte

| Componente | Herramienta |
| :--- | :--- |
| Lenguaje / entorno | Python 3.12 + `uv` (VS Code) |
| Extracción de documentos | `pdfplumber`, `python-docx` |
| Correo | IMAP estándar (`imaplib`) |
| IA | `google-genai` (Gemini), cliente OpenAI para Groq |
| Panel F3 | `streamlit` + pandas |
| API F4 | `fastapi` + `uvicorn` (solo localhost) |
| Programación del lote | `schedule` |

---

## 8. Arquitectura y componentes

```
Agente_RRHH/
├── main.py                     # CLI raíz (punto de entrada único)
├── prompt/                     # prompts de IA editables (.md)
│   ├── extractor.md            #   F1 · texto → JSON
│   ├── evaluador.md            #   F2 · perfil + requisitos → evaluación
│   └── chatbot.md              #   F4 · narrativa opcional del chat
├── config/
│   ├── vacantes/               # requisitos por vacante (regla de negocio)
│   └── tarifas.json            # tarifas de referencia para el cálculo de costos
├── data/                       # datos de candidatos (NO se suben a git)
│   ├── bronze/                 # originales brutos por <fecha>/<vacante>/
│   ├── silver/candidatos/      # JSON estandarizados (idempotentes)
│   └── gold/                   # evaluaciones + ranking + bitácora de costos
├── logs/                       # logs de ejecución (ingesta.log)
└── src/agente_rrhh/
    ├── core/                   # denominador común: config, persistence, utilidades
    │   ├── config.py           # .env, estados, rutas (DATA_DIR, retención, etc.)
    │   ├── json_store.py / raw_store.py / gold_store.py   # capas bronze/silver/gold
    │   ├── sanitizer.py / logging_setup.py / vacantes.py
    │   ├── llm.py              # fachada única de IA (Gemini/Groq) + tokens
    │   ├── prompts.py          # carga de prompts y parseo de JSON
    │   └── costo.py            # bitácora y cálculo de costos (config/tarifas.json)
    ├── ingestion/              # FASE 1 (imap_client, extractor, agent_extractor, pipeline)
    ├── evaluation/             # FASE 2 (reglas.py, agente_evaluador, pipeline_evaluacion)
    ├── dashboard/              # FASE 3 (consultas.py lectura, app.py UI)
    └── chatbot/                # FASE 4 (motor, sesion, simulador, api, frontend)
```

Principios de diseño:

- **`core/` como denominador común**: configuración, persistencia y utilidades
  se comparten entre fases; nada se duplica.
- **Fases desacopladas pero importables entre sí**; lo reutilizable se
  promueve a `core/`.
- **Punto de entrada único** (`main.py`): los comandos se documentan en la
  sección 11.
- **Reglas de negocio fuera del código de IA**: requisitos en `config/` y
  prompts en `prompt/`, ambos versionables.
- **UI en lenguaje de RRHH**: los términos técnicos internos (silver/gold,
  tokens, estados) quedan fuera de las interfaces hacia el usuario.

---

## 9. Seguridad y privacidad

- **Credenciales**: únicamente en `.env` (ignorado por git); no se hardcodean
  ni se loguean secretos.
- **Datos personales**: `data/` y `logs/` no se suben a git. Los datos de los
  postulantes se usan **exclusivamente para la preselección**, nunca para
  entrenamiento de modelos comerciales.
- **Mitigación de sesgo**: el Agente 1 excluye explícitamente foto, edad,
  género, dirección y estado civil del JSON resultante. En F2, nombre, teléfono
  y correo se conservan solo para contacto/ranking y **no participan en la
  puntuación**.
- **Exposición**: los paneles F3 y F4 solo escuchan en **red local
  (`localhost` / `127.0.0.1`)**; no se exponen puertos a Internet.
- **Trazabilidad**: cada decisión queda en los documentos gold (requisitos
  evaluados, desglose, uso de tokens) y en el log del lote, permitiendo auditar
  cualquier resultado.

---

## 10. Costo del proyecto

| Componente | Modelo de costo |
| :--- | :--- |
| Lenguaje y herramientas | Python, uv, fastapi, streamlit, pdfplumber… todos libres: $0 |
| F1 · Agente Extractor | Gemini: capa gratuita con API Key; la ventana del lote es acotada (por fecha) y los ilegibles **no** se envían a la IA |
| F2 · Agente Evaluador | Groq: tier "Forever Free"; **1 llamada por candidato** y candidatos ya evaluados se omiten |
| F4 · Chatbot | **0 llamadas por defecto** (motor offline): las respuestas, tablas y simulaciones se calculan en código; la IA opcional se registra y audita |
| Monitoreo | Bitácora `data/gold/costo/uso_chat.jsonl` + sumas de tokens F2 (en cada documento gold) y tarifas editables en `config/tarifas.json`; el chat muestra el total y le avisa al área de talento |

El **objetivo de costo $0** se cumple por diseño: la IA se usa solo donde
aporta (extracción y evaluación), siempre por *free tier*, y el panel de costos
hace el gasto **visible y auditable** dentro de la propia aplicación.

---

## 11. Guía de uso

### 11.1 Requisitos

- Python 3.12 (`.python-version`) y gestor de dependencias `uv`.
- Cuenta de Gmail dedicada a postulaciones con **2FA** y **contraseña de
  aplicación** IMAP.
- Claves de IA (Gemini para F1; Groq para F2) configuradas en `.env`.

### 11.2 Variables principales del `.env`

```dotenv
EMAIL=tu_correo@gmail.com
API_EMAIL=xxxx xxxx xxxx xxxx          # App Password IMAP (16 caracteres)
ASUNTO=POSTULACION -
DIAS_ATRAS=1
GEMINI_API_KEY=tu_clave
MODELO_GEMINI=gemini-3.5-flash
GROQ_API_KEY=tu_clave_groq
PROVEEDOR_EVALUADOR=groq
MODELO_EVALUADOR=openai/gpt-oss-120b
DATA_DIR=data
PROVEEDOR_CHAT=                        # vacío = chat offline, costo $0
```

### 11.3 Comandos

```bash
uv run python main.py                  # F1 · lote real (IMAP + Gemini + silver)
uv run python main.py --dry-run        # F1 · valida el flujo sin gastar cuota
uv run python main.py limpiar          # F1 · purga bronze según retención de .env
uv run python main.py evaluar          # F2 · evalúa todos los candidatos "Listo"
uv run python main.py dashboard --port 8501   # F3 · panel Streamlit (localhost)
uv run python main.py chat --port 8510        # F4 · chatbot web (127.0.0.1)
```

- `--dry-run` extrae y sanitiza **sin** llamar a la IA, sin escribir silver y
  sin marcar correos como leídos: ideal para validar el flujo y la rotación de
  claves.
- `limpiar` deduplica copias repetidas y borra de bronze los originales con más
  de `RAWDATA_RETENCION_DIAS` días (retiene la configurable en `.env`).

### 11.4 Salidas

- **bronze** · copia idempotente de cada adjunto usado (se conserva aunque
  resulte ilegible, para revisión manual).
- **silver** · un JSON por candidato (datos estandarizados + estado).
- **gold** · evaluación por candidato (score, desglose, fortalezas/brechas,
  uso de tokens) y `ranking.json` por vacante.
- **logs/ingesta.log** · trazabilidad del lote (asunto → remitente → estado).

---

## 12. Resultados esperados y KPIs

| KPI | Meta |
| :--- | :--- |
| Tiempo de respuesta de una consulta de ranking (F3) | < 3 s sobre archivos locales |
| Procesamiento de un lote diario (~30 CVs) | Automático, sin intervención |
| Costo operativo | $0 (free tiers) + gasto de IA auditado y visible en la app |
| Reproducibilidad del puntaje | Mismo `match_score` sin importar quién ejecute |
| Trazabilidad | Toda decisión documentada (requisitos, desglose, tokens) |
| Mitigación de sesgo | Atributos personales excluidos desde F1; no puntúan en F2 |

Beneficios cualitativos: reducción del tiempo manual de preselección, criterio
único y explicable entre vacantes, y una base clara para **mejora continua de
los requisitos** (las brechas de mercado detectadas en F4 permiten ajustar las
vacantes a la realidad del pool de aplicantes).

---

## 13. Conclusiones y recomendaciones

**Conclusiones**

1. Es posible automatizar la preselección **sin infraestructura de pago**: la
   combinación de free tiers, persistencia en archivos y un motor de consulta
   en código logra un sistema funcional con **costo $0**.
2. Separar el **cálculo de reglas** (en código) del **entendimiento semántico**
   (en la IA) garantiza que los puntajes sean reproducibles y defendibles,
   aún cuando el modelo cambie.
3. La mitigación de sesgo es viable si se aplica **desde el origen** de los
   datos (F1), no como una corrección posterior.
4. La arquitectura medallion separa claramente "recibido", "estandarizado" y
   "evaluado", lo que hace el sistema **auditable** y fácil de explicar al área
   usuaria.

**Recomendaciones**

- Mantener el prompt de cada agente (`.md`) y los requisitos (`config/`)
  **versionados** para auditar cambios en la regla de negocio.
- Revisar periódicamente la ventana de búsqueda (`DIAS_ATRAS`), el modelo de
  Gemini/Groq disponible y las tarifas de `config/tarifas.json`.
- Validar los umbrales 80/50 con datos reales del área para confirmar que la
  sugerencia de fase técnica calibra con la calidad histórica de los
  contratados.
- Sensibilizar al equipo de talento sobre los fundamentos del `match_score`
  para que la herramienta se use como **primer filtro complementario**, no como
  decisor aislado.

---

## 14. Trabajo futuro / Roadmap

Prioridad por tipo de mejora y retorno:

1. **Persistencia de sesiones del chat** — el contexto ligero (vacante/candidato
   en foco) se mantiene en memoria; persistirlo evita perderlo al reiniciar el
   proceso.
2. **Historial de conversación** opcional en F4 para reusar consultas.
3. **Nuevos proveedores de IA en la fachada `core/llm.py`** (OpenRouter,
   Cerebras u Ollama local) para ampliar las opciones del chat y de la
   evaluación sin tocar el resto del sistema.
4. **Evolución de la persistencia** a SQLite (y, en su caso, PostgreSQL o
   MongoDB gestionados) cuando el volumen o la concurrencia lo justifiquen,
   conservando las capas medallion.
5. **Lote F1 con `--programar`** activado en producción (agenda diaria con
   `schedule`) para operar sin intervención.
6. **Más utilidades del chat** basadas en los datos gold (p. ej. análisis por
   carrera o por bloque de experiencia) manteniendo la regla de costo $0.

---

## 15. Bibliografía y referencias

Documentación y fuentes utilizadas para las decisiones técnicas:

- **Medallion Architecture** — *Databricks*:
  https://www.databricks.com/glossary/medallion-architecture
- **Gemini API / Google AI Studio** (generación + extracción con modelos de
  lenguaje): https://ai.google.dev/docs
- **Groq: API compatible OpenAI y catálogo de modelos**:
  https://console.groq.com/docs
- **equivale a estándar `imaplib` de Python (IMAP4 SSL)**:
  https://docs.python.org/3/library/imaplib.html
- **FastAPI (API web, servido solo en localhost)**:
  https://fastapi.tiangolo.com
- **Streamlit (paneles de datos interactivos)**:
  https://docs.streamlit.io
- **U.S. EEOC — *Americans with Disabilities Act and the Use of Software,
  Algorithms, and Artificial Intelligence in Hiring* (guía sobre el uso de IA
  en selección y sus riesgos de sesgo)**:
  https://www.eeoc.gov/laws/guidance/americans-disabilities-act-and-use-software-algorithms-and-artificial
- **SHRM — recursos sobre reclutamiento/false positives y criterios de
  preselección**:
  https://www.shrm.org