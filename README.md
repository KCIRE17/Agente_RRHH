# Agente RRHH — Sistema Multiagente de Preselección de Talento

Documentación del proyecto de inicio a fin: visión, fases, arquitectura,
especificación técnica, configuración y uso.

---

## 1. Visión

Automatizar la **preselección de talento**: el sistema recibe postulaciones de
candidatos por correo (Gmail vía IMAP), extrae la información de sus
currículums, la **estandariza** con una IA, la **evalúa objetivamente** frente
a los requisitos de cada vacante y presenta un **ranking** en un dashboard
interactivo, todo con **costo operativo $0** (herramientas libres y *free
tiers* de las APIs de IA).

### Fases del proyecto

| Fase | Nombre | Agente | Estado |
| :--- | :--- | :--- | :--- |
| **F1** | Ingesta y Extracción de Candidaturas | Agente 1 (Gemini, por `MODELO_GEMINI`) | ✅ Implementada |
| **F2** | Evaluación y Match Score | Agente 2 (Groq, por `MODELO_EVALUADOR`/`PROVEEDOR_EVALUADOR`) | ✅ Implementada |
| **F3** | Dashboard y Visualización (Streamlit) | — | ✅ Implementada |
| **F4** | Chatbot de consultas de RRHH | — | 🟡 Esqueleto |

> El estado y los pendientes de cada fase se controlan en **`PENDIENTES.md`**
> (bitácora Scrum).

---

## 2. Requerimientos

### 2.1 Funcionales (por fase)

- **F1 — Carga e Ingesta de Documentos:** recibir hasta ~30 CVs diarios
  (PDF, DOCX, TXT, MD) desde el correo de postulaciones.
- **F1 — Extracción y Estandarización (Agente 1):** con IA, identificar los
  encabezados del CV sin importar su redacción ("Experiencia", "Trayectoria")
  y transformarlos a un formato **JSON estandarizado**.
- **F2 — Evaluación y Comparación Objetiva (Agente 2):** comparar el perfil
  del candidato con los requisitos técnicos de la vacante con ponderación
  fija: **Habilidades 50 %, Experiencia 30 %, Formación 20 %**.
- **Mitigación de sesgos:** excluir del cálculo atributos personales no
  pertinentes (fotografía, género, edad, dirección, estado civil).
- **F2 — Match Score y Clasificación:** puntaje 0–100 % clasificado en
  **Alta (80–100 %), Media (50–79 %), Baja (< 50 %)**.
- **F2 — Fortalezas y Brechas:** reporte de fortalezas y requisitos faltantes
  (puntaje 0 + alerta si un campo obligatorio no existe).
- **Gestión de errores de lectura:** registrar el motivo del fallo y sugerir
  revisión manual.
- **F3 — Dashboard y Visualización:** interfaz Streamlit con el ranking de
  candidatos, puntajes e información detallada.
- **F4 — Chatbot:** consultas del encargado de RRHH sobre la información
  procesada (ej. recomendaciones para la fase técnica).

### 2.2 No funcionales

- **Costo $0**: solo herramientas libres y capas gratuitas de las APIs.
- **Persistencia local**: CVs estructurados, evaluaciones, puntajes e
  historial almacenados en la carpeta `data/` con **arquitectura medallion**
  (bronze/silver/gold); sin depender de servicios en la nube.
- **Privacidad y seguridad**: los datos de los postulantes se usan
  exclusivamente para la preselección; no se exponen a servidores comerciales
  externos para entrenamiento.
- **Usabilidad**: interfaz intuitiva; el analista selecciona la vacante y ve
  resultados rápidamente.

### 2.3 Técnicos y de entorno

- **Entorno**: desarrollo local en **VS Code**.
- **Lenguaje**: **Python 3.12** + gestor de dependencias **uv**.
- **Procesamiento**: `pdfplumber` (PDFs), `python-docx` (Word).
- **IA**: Gemini (Agente Extractor; modelo por `MODELO_GEMINI`); Groq vía API
  compatible OpenAI (Agente Evaluador; proveedor/modelo por
  `PROVEEDOR_EVALUADOR`/`MODELO_EVALUADOR`, default `openai/gpt-oss-120b`).
- **Dashboard**: Streamlit 1.6x (con pandas) — panel local interactivo F3.

---

## 3. Arquitectura y estructura del proyecto

```
Agente_RRHH/
├── main.py                    # CLI raíz (punto de entrada único)
├── pyproject.toml             # dependencias (uv)
├── .env                       # credenciales (NO subir a git)
├── README.md                  # este documento (documentación completa)
├── PENDIENTES.md              # bitácora Scrum de pendientes
├── AGENTS.md                  # convenciones para agentes de IA
├── .streamlit/config.toml     # tema del dashboard (Streamlit)
├── logs/                      # logs de ejecución (ingesta.log)
├── prompt/                    # prompts de IA editables (.md)
│   ├── extractor.md           #   prompt del Agente Extractor (F1)
│   └── evaluador.md           #   prompt del Agente Evaluador (F2)
├── config/
│   └── vacantes/              # requisitos por vacante (regla de negocio)
│       └── ANALISTA_DE_DATOS.json
├── data/                      # datos de candidatos (dato personal, NO a git)
│   ├── bronze/                # originales brutos por <fecha>/<vacante>/
│   ├── silver/                # candidatos JSON estandarizados (idempotentes)
│   │   └── candidatos/        #   <sha1(mensaje_id)>.json
│   └── gold/                  # evaluaciones/rankings (F2+)
│       └── evaluacion/        #   <vacante_id>/<id_candidato>.json + ranking.json
└── src/agente_rrhh/
    ├── core/                  # base común a TODAS las fases
    │   ├── config.py          # .env, estados, parámetros (DATA_DIR, ASUNTO, ...)
    │   ├── json_store.py      # capa silver: un JSON por candidato (idempotente)
    │   ├── sanitizer.py       # normalización de texto (sin tildes, UTF-8)
    │   ├── raw_store.py       # capa bronze: originales + purga/dedupe
    │   ├── logging_setup.py   # logging consola + archivo
    │   ├── llm.py             # fachada IA: Gemini o Groq (+ uso de tokens)
    │   ├── prompts.py         # carga de prompts .md y parseo JSON de la IA
    │   ├── vacantes.py        # requisitos por vacante (config/vacantes/)
    │   └── gold_store.py      # capa gold: evaluaciones + ranking, escritura atómica
    ├── ingestion/             # FASE 1 — Ingesta y Extracción (Agente 1)
    │   ├── imap_client.py     # IMAP SSL, filtro asunto/fecha, BODY.PEEK[]
    │   ├── extractor.py       # texto de PDF/DOCX/TXT/MD + errores (Ilegible/Formato)
    │   ├── agent_extractor.py # Gemini: texto → JSON (prompt desde prompt/)
    │   └── pipeline.py        # orquestación del lote + reintentos IA
    ├── evaluation/            # FASE 2 — Match Score (Agente 2)
    │   ├── reglas.py          # pesos 50/30/20 y umbrales Alta/Media/Baja
    │   ├── agente_evaluador.py# Groq: perfil + requisitos → JSON (prompt/ing)
    │   └── pipeline_evaluacion.py # silver "Listo" → gold (evaluación + ranking)
    ├── dashboard/             # FASE 3 — Dashboard Streamlit
    │   ├── consultas.py       #   lectura gold/silver (sin UI)
    │   └── app.py             #   UI (Ranking de postulantes / Postulante /
    │                          #   Postulaciones / Metodología)
    └── chatbot/               # FASE 4 — Chatbot de consultas [ESQUELETO]
```

**Reglas de estructura**

- `core/` es el denominador común: configuración, persistencia y utilidades
  que ninguna fase debe duplicar.
- Cada fase vive en su subpaquete. Las fases **pueden importarse entre sí**,
  pero lo reutilizable se promueve a `core/`.
- Imports relativos dentro del paquete: `from ..core.config import ...`.
- Punto de entrada único: `main.py` en la raíz.

---

## 4. Especificación — FASE 1: Ingesta y Extracción de Candidaturas

### 4.1 Flujo operativo

```
[ Bandeja de entrada email ]
        │  (lote / trigger temporal)
        ▼
[ Conexión IMAP & filtro ]  →  busca UNSEEN + asunto (ASUNTO) + fecha (DIAS_ATRAS)
        │
        ▼
[ Extracción & sanitización ]  →  .pdf, .docx, .txt, .md (o cuerpo del correo)
        │
        ▼
[ Agente Extractor (Gemini, prompt/prompt/extractor.md) ]  →  JSON estandarizado
        │
        ▼
[ data/bronze (original) + data/silver/candidatos/<hash>.json ]
```

**Triggers de proceso (Agente 1):**

1. **Sintaxis de entrada**: asunto `POSTULACION - <Nombre del Puesto>`
   (prefijo configurable `ASUNTO`); formatos `.pdf`, `.docx`, `.txt`, `.md`.
2. **Disparo por lotes**: ejecución programada (ej. 18:00) con Task
   Scheduler/cron o la librería `schedule`, para no consumir RAM ni exceder
   la cuota gratuita de la API.
3. **IMAP**: conexión cifrada a `imap.gmail.com:993` (`imaplib`), login con
   **contraseña de aplicación**, búsqueda `UNSEEN` filtrada por asunto y
   fecha **en el servidor** (evita escanear el buzón completo) usando
   `BODY.PEEK[]` (no marca correos como leídos al inspeccionarlos).
4. **Extracción**: `pdfplumber` (PDF), `python-docx` (DOCX), lectura estándar
   (TXT/MD); si hay varios adjuntos se prueban todos hasta encontrar uno
   legible; fallback al cuerpo del correo si ninguno sirve.
   Los PDFs escaneados (imagen sin texto) o corruptos se detectan y no se
   envían a la IA (se preserva la cuota).
5. **Sanitización**: normalización UTF-8, remoción de tildes y de espacios
   redundantes.
6. **Estandarización (Agente 1)**: el texto saneado se envía al modelo de
   Gemini configurado (`MODELO_GEMINI`) con el prompt de
   `prompt/extractor.md`, que unifica sinónimos de encabezados ("Trayectoria"
   → `experiencia_laboral`) y **excluye deliberadamente** los atributos de
   sesgo (foto, edad, género, dirección, estado civil).
7. **Persistencia**: se guarda el JSON en `data/silver/candidatos/` con nombre
   `sha1(mensaje_id).json` (**idempotencia** por archivo) + **copia del
   archivo original** en `data/bronze/<fecha>/<vacante>/`.

### 4.2 Documento del candidato (capa silver)

Un archivo JSON por candidato en `data/silver/candidatos/` (nombre =
`sha1(mensaje_id)`):

| Campo | Contenido |
| :--- | :--- |
| `mensaje_id` | Message-ID de Gmail (único; idempotencia). Si falta, hash de respaldo |
| `id_candidato` | Identificador hex de 32 caracteres (UUID sin guiones) |
| `vacante_id` | Puesto extraído del asunto |
| `email_remitente` / `remitente_metadatos` | From crudo + `{nombre, email, dominio}` |
| `fecha_envio` / `fecha_ingesta` | Cabecera `Date` / momento de extracción (ISO UTC) |
| `x_mailer` | Cliente de correo usado (cabecera `X-Mailer`) |
| `ruta_archivo_raw` | Ruta del archivo original en `data/bronze/` |
| `formato_origen` | PDF / DOCX / TXT / MD / CORREO |
| `datos_json` | Salida estandarizada del Agente 1 |
| `texto_crudo` | Texto saneado conservado (solo para reintentos IA) |
| `estado_procesamiento` | Ver matriz de excepciones |
| `motivo` | Descripción del error (o `null`) |
| `fecha_reintento` | Último reintento IA exitoso (si aplica) |

### 4.3 Matriz de excepciones y control de errores

| Escenario | Acción del sistema | Estado registrado |
| :--- | :--- | :--- |
| El asunto no cumple `ASUNTO` | Se omite el correo | N/A |
| Adjunto corrupto o PDF de imagen | Se interrumpe el flujo a la IA | `Error: Archivo Ilegible` |
| Formato de adjunto no permitido | Se omite la lectura | `Error: Formato No Permitido` |
| Fallo o pérdida de conexión con la API de IA | Se conserva el texto para el siguiente lote | `Pendiente: Reintento IA` |
| Procesamiento exitoso | Extracción + JSON | `Listo para Evaluación` |

### 4.4 JSON resultante del Agente Extractor

```json
{
  "candidato": {
    "email_remitente": "postulante@email.com",
    "formato_origen": "PDF"
  },
  "datos_contacto": {
    "nombre_completo": "Nombre Apellido",
    "telefono": "51987654321",
    "email": "postulante@email.com"
  },
  "datos_estructurados": {
    "habilidades": ["Python", "SQL", "Power BI", "Git"],
    "experiencia_laboral": [
      {
        "puesto": "Analista de Datos Junior",
        "duracion_anos": 1.5,
        "descripcion": "Desarrollo de dashboards y consultas SQL en entornos locales."
      }
    ],
    "formacion_academica": [
      {
        "grado": "Egresado",
        "carrera": "Ingeniería de Sistemas",
        "institucion": "Universidad Nacional Mayor de San Marcos"
      }
    ],
    "certificaciones": ["Power BI Data Analyst"]
  },
  "control_sesgo": {
    "atributos_excluidos": ["foto", "edad", "genero", "direccion", "estado_civil"]
  }
}
```

### 4.5 Prompts configurables

Los prompts de IA viven en **`prompt/`** como archivos `.md` editables (no en
código). El Agente Extractor usa `prompt/extractor.md` (configurable con
`PROMPT_EXTRACTOR`). El placeholder `{{texto_candidato}}` se sustituye con el
texto del candidato en cada llamada y `{{requisitos_vacante}}` con los
requisitos en F2. Si el archivo falta, el lote lo reporta con un error
claro. F4 podrá añadir `prompt/chatbot.md`.

---

## 5. Especificación — FASE 2: Evaluación y Match Score

### 5.1 Requisitos de la vacante (regla de negocio)

Los requisitos viven en **`config/vacantes/<SLUG>.json`**, editables sin tocar
código y versionables en git. El slug se deriva del `vacante_id` (mayúsculas,
sin tildes, espacios → `_`; ej. `ANALISTA DE DATOS` → `ANALISTA_DE_DATOS.json`).
El directorio se configura con `RUTA_VACANTES`.

```json
{
  "vacante_id": "ANALISTA DE DATOS",
  "requisitos": {
    "habilidades": {
      "esenciales": ["Python", "Microsoft SQL Server", "Power BI", "Excel",
                     "Pensamiento analítico", "Resolución de problemas"],
      "opcionales": ["Oracle", "C++", "Java", "Office", "Inglés",
                     "Trabajo en equipo", "Organizado",
                     "Orientación a resultados", "Adaptabilidad",
                     "Mejora Continua"]
    },
    "experiencia_minima_anos": 0,
    "formacion": {
      "carreras": ["Ingeniería de Sistemas", "Ingeniería de Datos",
                   "Estadística", "Ciencias de la Computación"]
    }
  }
}
```

Un candidato sin requisitos configurados para su vacante se omite con aviso en
el log (el documento gold guarda los requisitos usados para trazabilidad).

### 5.2 Flujo operativo

```
[ data/silver/candidatos/*.json ]  →  filtro estado "Listo para Evaluación"
        │                                    (+ opcional --vacante)
        ▼
[ Core ]  →  cargar requisitos de config/vacantes/<slug>.json
        │
        ▼
[ Agente Evaluador (Groq, prompt/prompt/evaluador.md) ]  →  JSON de evaluación
        │
        ▼
[ reglas.py ]  →  score compuesto 50/30/20 + clasificación y clamps a 0–100
        │
        ▼
[ data/gold/evaluacion/<vacante>/<id>.json ]  +  ranking.json (ordenado desc)
```

- **1 sola llamada de IA por candidato** (minimiza cuota): el prompt lleva el
  perfil del candidato y los requisitos de la vacante; el score final y la
  clasificación se **calculan en código** con `evaluation/reglas.py` (el modelo
  propone un `desglose_puntos` por bloque que se compone y valida localmente).
- Los atributos sensibles para contacto pasan al documento gold (nombre,
  teléfono, correo); NO se usan en la puntuación (bloqueo de sesgo en F1).
- **Idempotencia**: un candidato ya evaluado se omite en lotes siguientes.

### 5.3 Documento de evaluación (capa gold)

| Campo | Contenido |
| :--- | :--- |
| `id_candidato`, `vacante_id`, `mensaje_id` | Identificadores (idempotencia) |
| `nombre_completo`, `telefono`, `email_remitente` | Datos de contacto (no puntúan) |
| `fecha_envio` / `fecha_evaluacion` | Cabecera / momento de la evaluación (ISO) |
| `match_score` | Puntaje 0–100 calculado por `reglas.py` |
| `clasificacion` | `Alta` (≥80), `Media` (≥50), `Baja` (<50) |
| `desglose` | Peso, parcial y puntos por bloque (habilidades/experiencia/formación) |
| `fortalezas` / `brechas` | Listas que reporta la IA |
| `requisito_esencial_ausente` | Alertas de campos obligatorios sin evidencia |
| `requisitos_evaluados` | Snapshot de los requisitos usados |
| `proveedor` / `modelo` / `uso_tokens` | Trazabilidad de la llamada (tokens del prompt, completado y total) |
| `estado_procesamiento` | `Evaluado` (o `Pendiente: Reintento Evaluación`) |

### 5.4 Matriz de excepciones (F2)

| Escenario | Acción del sistema | Estado registrado |
| :--- | :--- | :--- |
| Sin requisitos para la vacante | Se omite y se avisa en el log | N/A |
| Candidato ya evaluado | Se omite (idempotencia) | `Evaluado` (previo) |
| Fallo de la API de IA o JSON inválido | No se escribe gold; reintenta en el siguiente lote | `Pendiente: Reintento Evaluación` |
| Éxito | Evaluación + ranking | `Evaluado` |

---

## 6. Especificación — FASE 3: Dashboard y Visualización (Streamlit)

Panel local interactivo para el área de RRHH. Lee directamente de **gold**
(rankings y evaluaciones) y **silver** (resumen de ingesta); no toca la IA ni
las fases de escritura.

### 6.1 Vistas

| Vista | Contenido |
| :--- | :--- |
| **Ranking de postulantes** | Vacante → métricas (postulantes evaluados, compatibilidad alta/media/baja, puntaje promedio), tabla con puntaje y nivel (filtrable) y distribución |
| **Postulante** | Puntaje de compatibilidad, nivel, datos de contacto, fortalezas, aspectos por reforzar (con requisitos indispensables faltantes resaltados), resumen del análisis, explicación del cálculo y resumen de la hoja de vida |
| **Postulaciones** | Resumen de lo recibido por situación y por vacante; avisa postulaciones pendientes de evaluación |
| **Metodología** | Explicación en lenguaje de RRHH: proceso en 4 pasos, fórmula 50/30/20, niveles de compatibilidad, evaluación sin sesgos y significado de cada situación |

Todo el panel usa **lenguaje del área de talento**: los términos internos
(silver/gold, estados técnicos, tokens) quedan fuera de la interfaz.

### 6.2 Reglas de negocio del dashboard

- **Sugerencia RRHH** (estática, no IA): **Alta** → "Pase a fase técnica",
  **Media** → "Revisión manual", **Baja** → "No avanza".
- **Candidatos evaluados** se derivan de **gold** (F2 no muta silver);
  "listos" = total − evaluados − errores − reintentos.
- Lecturas cacheadas 30 s + botón "Actualizar información" (cumple el listo de F3:
  consulta real en menos de 3 s sobre archivos locales).

### 6.3 Estructura

- `src/agente_rrhh/dashboard/consultas.py` — capa de lectura (gold/silver),
  independiente de Streamlit y testeable.
- `src/agente_rrhh/dashboard/app.py` — UI (Ranking de postulantes /
  Postulante / Postulaciones / Metodología).
- `.streamlit/config.toml` — tema visual (colores, fuente).

### 6.4 Definición de listo

- [x] Una consulta de ranking de una vacante real responde en < 3 s desde la
  interfaz con los datos de silver/gold.

---

## 7. Configuración y uso

### 7.1 Requisitos

- Python **3.12** (`.python-version`), gestor **uv**, editor **VS Code**.
- Una cuenta de Gmail dedicada al proceso de selección con **2FA activado**.
- Sin dependencias externas de bases de datos (persistencia en archivos).

### 7.2 Instalación de dependencias

```bash
uv add python-dotenv pdfplumber python-docx google-genai schedule
```

| Librería | Función |
| :--- | :--- |
| `python-dotenv` | Lee el archivo `.env` |
| `pdfplumber` | Extrae texto de PDFs |
| `python-docx` | Extrae texto de Word (`.docx`) |
| `google-genai` | Llama a **Gemini** (Agente Extractor; modelo por `MODELO_GEMINI`) |
| `openai` | Cliente para **Groq** (Agente Evaluador; endpoint compatible OpenAI) |
| `schedule` | Ejecución programada (`--programar`) |
| `streamlit` | Dashboard interactivo F3 (incluye pandas) |

> `imaplib` (IMAP a Gmail) es parte de la librería estándar: no se instala.

### 7.3 Variables del `.env`

```dotenv
# 1) Cuenta de correo y acceso IMAP
EMAIL=tu_correo@gmail.com
API_EMAIL=xxxx xxxx xxxx xxxx    # App Password IMAP (16 caracteres)
# PASSWORD=                      # opcional: respaldo de API_EMAIL
IMAP_TIMEOUT=30                  # timeout de conexión IMAP (segundos)

# 1b) Asunto, ventana de búsqueda y agenda
ASUNTO=POSTULACION -             # prefijo de asunto de postulaciones
DIAS_ATRAS=1                     # días hacia atrás (0 = sin límite)
HORA_INGESTA=18:00               # hora del lote programado (--programar)

# 2) Gemini (Agente Extractor)
GEMINI_API_KEY=tu_clave_AiZa...  # requerida
MODELO_GEMINI=gemini-3.5-flash   # modelo (opcional)
PROMPT_EXTRACTOR=prompt/extractor.md   # prompt del extractor (opcional)

# 3) Evaluación (F2 — Groq, Agente Evaluador)
GROQ_API_KEY=tu_clave_groq            # requiere PROVEEDOR_EVALUADOR=groq
PROVEEDOR_EVALUADOR=groq              # proveedor del Agente Evaluador
MODELO_EVALUADOR=openai/gpt-oss-120b  # modelo (ver modelos disponibles)
PROMPT_EVALUADOR=prompt/evaluador.md  # prompt del evaluador (opcional)

# 4) Persistencia (arquitectura medallion)
DATA_DIR=data                    # raíz de datos (bronze/silver/gold)
RAWDATA_RETENCION_DIAS=90        # retención de originales en bronze
RUTA_VACANTES=config/vacantes    # requisitos por vacante (regla de negocio)
```

- **`EMAIL`** — usuario de la conexión IMAP (tu cuenta Gmail).
- **`API_EMAIL` / `PASSWORD`** — **contraseña de aplicación** de Gmail, **NO**
  la contraseña personal. Se genera en `myaccount.google.com/apppasswords`
  (16 caracteres, formato `xxxx xxxx xxxx xxxx`). La App Password también se
  permite en `PASSWORD` como respaldo.
- **`IMAP_TIMEOUT`** — segundos de espera de la conexión IMAP (default `30`).
- **`ASUNTO`** — prefijo que define las postulaciones. Filtro en servidor por
  primera palabra + verificación local de que el asunto comienza con el
  prefijo; `vacante_id` = todo lo que sigue.
- **`DIAS_ATRAS`** — ventana de días hacia atrás (`1` = hoy; `0` = sin límite
  de fecha, más lento).
- **`HORA_INGESTA`** — hora del lote diario programado con `--programar`
  (default `18:00`).
- **`GEMINI_API_KEY`** — clave de la API de Gemini en
  `aistudio.google.com/apikey`. **Requerida**: sin ella, los candidatos
  válidos quedan en `Pendiente: Reintento IA`.
- **`MODELO_GEMINI`** — nombre del modelo de Gemini (default
  `gemini-3.5-flash`). Cambiar si la API Key tiene acceso a otro modelo.
- **`PROMPT_EXTRACTOR`** — ruta del prompt Markdown del extractor (default
  `prompt/extractor.md`).
- **`GROQ_API_KEY`** — clave de Groq en `console.groq.com` (tier "Forever
  Free", sin tarjeta). Requerida por F2 fuera de `--dry-run`.
- **`PROVEEDOR_EVALUADOR`** — proveedor del Agente Evaluador (`groq`, por
  ahora). Default `groq`.
- **`MODELO_EVALUADOR`** — modelo del evaluador (default
  `openai/gpt-oss-120b`); se consultan los disponibles con
  `GET /openai/v1/models` (el modelo exacto depende de la cuenta).
- **`PROMPT_EVALUADOR`** — ruta del prompt Markdown del evaluador (default
  `prompt/evaluador.md`).
- **`DATA_DIR`** — raíz de la arquitectura medallion (default `data`).
- **`RAWDATA_RETENCION_DIAS`** — antigüedad máxima de los originales de bronze
  durante `limpiar` (default `90`).
- **`RUTA_VACANTES`** — directorio con los requisitos por vacante (default
  `config/vacantes`).

### 7.4 Ejecución

```bash
uv run python main.py                  # F1: lote real (IMAP + Gemini + silver)
uv run python main.py --dry-run        # F1: sin gastar cuota ni guardar en silver
uv run python main.py --max 5          # F1: procesa máximo 5 correos
uv run python main.py --programar      # F1: lote diario a HORA_INGESTA (loop)
uv run python main.py limpiar          # F1: purga bronze (retención del .env)
uv run python main.py limpiar --dias 7 # F1: purga bronze de más de 7 días
uv run python main.py evaluar [--vacante "ANALISTA DE DATOS"]  # F2: evaluación real
uv run python main.py evaluar --dry-run            # F2: simula sin llamar a Groq
uv run python main.py evaluar --verbose            # F2: logs DEBUG
uv run python main.py dashboard [--port 8501]      # F3: panel Streamlit
```

- **`--dry-run`**: extrae y sanitiza, pero **no llama a Gemini, no guarda en
  `silver/` y no marca correos como leídos**. Sí deja la copia idempotente en
  `data/bronze/` (no consume cuota de la API). Ideal para validar el flujo.
- **`--programar`** agenda el lote diario a `HORA_INGESTA`.
- **`limpiar`** deduplica copias `_<uuid>` repetidas y borra de `bronze/` los
  archivos con más de `--dias` días (default `RAWDATA_RETENCION_DIAS`).
- **`evaluar`** lee silver (`Listo para Evaluación`), evalúa contra
  `config/vacantes/` y escribe `data/gold/`. Sin `--vacante` procesa todos los
  candidatos listos. `--dry-run` simula la evaluación sin llamar a Groq.
- **`dashboard`** abre el panel Streamlit en
  `http://localhost:8501` (puerto con `--port`). Se recomienda **solo red
  local**: muestra datos personales de candidatos.

### 7.5 Salidas

- **`data/bronze/<fecha_envio>/<vacante>/<archivo>`** — copia idempotente del
  adjunto usado (o del cuerpo como `.txt`); se conserva aunque el PDF resulte
  ilegible, para revisión manual.
- **`data/silver/candidatos/<sha1(mensaje_id)>.json`** — un documento por
  candidato (estado, JSON estandarizado y metadatos).
- **`data/gold/evaluacion/<vacante>/<id_candidato>.json`** — evaluación F2 por
  candidato (score, desglose, fortalezas/brechas, uso de tokens).
- **`data/gold/evaluacion/<vacante>/ranking.json`** — ranking ordenado (score
  desc) que alimenta el dashboard F3.
- **`logs/ingesta.log`** — trazabilidad del lote (asunto → remitente →
  estado), más el resumen final.

---

## 8. Seguridad

- Las credenciales viven **solo** en `.env` (ignorado por git); nunca se
  hardcodean ni se loguean secretos.
- `data/` y `logs/` contienen **datos personales** de postulantes y no se
  suben a git.
- El Agente 1 descarta explícitamente foto, edad, género, dirección y estado
  civil del JSON resultante. F2 solo recibe, a efectos de contacto/ranking,
  nombre completo, teléfono y correo — que **no participan** en la puntuación.
- Los requisitos de vacante (`config/vacantes/`) y los prompts (`prompt/`) son
  regla de negocio y **sí** se versionan.
- El dashboard F3 muestra datos personales en pantalla: ejecutarlo **solo en
  red local** (no exponer el puerto a Internet).