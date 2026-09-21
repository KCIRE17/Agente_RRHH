# PROMPT MAESTRO — Generar el sistema «Agente RRHH» desde cero (limpio)

Úsalo así: copia este documento tal cual en una conversación nueva de IA (o
pásalo como archivo a un agente de código) y pide que ejecute el plan de abajo
en orden. El objetivo es reconstruir **el sistema completo, íntegro y limpio**,
sin archivos sobrantes, sin duplicación y sin comentarios decorativos.

---

## 0. Rol y objetivo

Actúa como **ingeniero senior de Python**. Construye un sistema local llamado
**Agente RRHH** que automatiza la *preselección de talento*:

1. Recibe postulaciones de candidatos por **Gmail vía IMAP** (adjuntos PDF,
   DOCX, TXT, MD o el cuerpo del correo).
2. Extrae y **estandariza** el CV a JSON usando **Gemini** (Agente 1 / F1).
3. **Evalúa** el perfil contra requisitos por vacante usando **Groq** (Agente 2 /
   F2) con peso fijo 50/30/20 y clasifica en Alta / Media / Baja.
4. Muestra el resultado en un **dashboard Streamlit** (F3).
5. Responde consultas del área de RRHH con un **chatbot web** (F4) cuyo motor
   funciona **100 % en código** (costo $0) con IA opcional.

No preguntes. Lee todo el documento y ejecútalo en el orden propuesto. Entrega
solo los archivos especificados; **no crees** extras, pruebas descartables ni
documentación que no se pida.

---

## 1. No negociables (reglas del sistema)

- **Entorno**: Python 3.12 (`uv` como gestor de dependencias), desarrollo en
  VS Code (Windows). Sin dependencias de bases de datos; persistencia en
  archivos JSON (arquitectura **medallion**).
- **Costo operativo $0**: solo herramientas libres y *free tiers* (Gemini F1,
  Groq F2). La capa de IA de F4 es **opcional y desactivada por defecto**.
- **`core/` es el denominador común**: configuración, persistencia y utilidades
  viven ahí para que ninguna fase duplique lógica. Toda llamada a las APIs de
  IA pasa sí o sí por `core/llm.py` (fachada única).
- **Fases separadas** en subpaquetes (`ingestion/`, `evaluation/`, `dashboard/`,
  `chatbot/`). Se permite importar entre fases, pero lo reutilizable se
  promueve a `core/`.
- **Imports relativos** dentro del paquete: `from ..core.config import ...`.
- **Punto de entrada único**: `main.py` en la raíz (CLI con argparse).
- **Credenciales únicamente en `.env`** (ignorado por git; se versiona solo
  `.env.example`). Nunca hardcodear ni loguear secretos.
  `tools/verificar_secretos.py` detecta claves/tokens (`gsk_`, `AIza...`,
  `AQ.Ab...` (formato 2025+ de claves Google), `sk-`, `ghp_`, bloques de clave
  privada) como hook pre-commit (`.githooks/pre-commit`; activar con
  `git config core.hooksPath .githooks`).
- **Control de acceso (login)**: el chatbot F4 (y **solo él**) pide
  autenticación con `ADMIN_USUARIO`/`ADMIN_CLAVE` del `.env`. Las credenciales
  sobreviven únicamente en `.env` (nunca en git ni en código). Si ambas están
  vacías, el login queda **desactivado con aviso visible** en la UI (para
  pruebas); si están cargadas, todo `/api/*` exige sesión. Comparación con
  `hmac.compare_digest` y tokens de sesión aleatorios (expiran a las 12 h). El
  dashboard F3 **no pide login** en este MVP.
- **`data/` y `logs/` contienen datos personales** de postulantes y **no se
  suben a git**.
- **Estados de procesamiento** exactos (constantes en `core/config.py`):
  - `Listo para Evaluación`
  - `Error: Archivo Ilegible`
  - `Error: Formato No Permitido`
  - `Pendiente: Reintento IA`
  - `Evaluado`
  - `Pendiente: Reintento Evaluación`
- **IA por fase, modelo distinto**: F1 → Gemini (`MODELO_GEMINI`); F2 → Groq
  (`MODELO_EVALUADOR` vía API compatible OpenAI). El proveedor F2 es **fijo
  `groq` en el código** (`PROVEEDOR_EVALUADOR` se lee del `.env` pero no cambia
  el proveedor efectivo). El chat F4 usa el proveedor `PROVEEDOR_CHAT`
  (`gemini` usa `GEMINI_API_KEY`; `groq` usa `GROQ_API_KEY`;
  `""`/`ninguno`/`none`/`offline` = offline, $0).
- **1 llamada de IA por candidato en F2**; `uso_tokens` se guarda en el
  documento gold (no hay agregador central; el control vive en el panel del
  proveedor).
- **Puntaje y clasificación se calculan en código** (`evaluation/reglas.py`),
  nunca se confía ciegamente en el `match_score` que proponga la IA: la IA
  propone un `desglose` por bloque y el código los recomponer con pesos
  **50/30/20**, umbrales **Alta ≥ 80, Media ≥ 50, Baja < 50** y **clamps 0‑100**.
- **Mitigación de sesgos**: atributos personales no pertinentes (foto, edad,
  género, dirección, estado civil) se excluyen deliberadamente en F1 y **no
  participan** en la puntuación.
- **Idempotencia**:
  - F1: un JSON por candidato llamado `sha1(mensaje_id).json` en
    `data/silver/candidatos/`; si ya existe se omite y se marca el correo leído.
  - F2: un candidato ya evaluado (gold) se omite en lotes siguientes.
- **Requisitos por vacante**: regla de negocio versionable en
  `config/vacantes/<SLUG>.json`. Slug = `vacante_id` en mayúsculas, sin tildes
  y con espacios → `_` (ej. `ANALISTA DE DATOS` → `ANALISTA_DE_DATOS.json`).
  Candidatos sin requisitos configurados se omiten con aviso en el log.
- **Prompts de IA editables** en `prompt/*.md` (no en código), con placeholders
  `{{texto_candidato}}` (F1), `{{requisitos_vacante}}` y `{{perfil_candidato}}`
  (F2), y `{{pregunta}}` / `{{contexto_datos}}` / `{{entidad_en_foco}}` (F4).
- **Sin comentarios decorativos** en el código: solo docstrings de módulo y
  comentarios útiles. Todo en español, consistente.

---

## 2. Estructura de directorios objetivo

Crear **exactamente** este árbol (vacíos los directorios de datos y logs):

```
agente_rrhh/
├── main.py                    # CLI raíz (punto de entrada único)
├── pyproject.toml             # dependencias (uv)
├── uv.lock                    # lockfile de dependencias (uv)
├── .python-version            # 3.12
├── .env.example               # plantilla de variables (sin secretos)
├── .gitignore                 # protege .env, data/, logs/ (NO data_demo/, que sí se versiona)
├── README.md                  # documentación completa del sistema
├── PENDIENTES.md              # bitácora Scrum del proyecto
├── AGENTS.md                  # convenciones para agentes de IA
├── PROMPT_GENERADOR_SISTEMA.md # esta plantilla maestra (regenerable)
├── DOCUMENTACION.md           # documentación histórica/de detalle (opcional)
├── .githooks/
│   └── pre-commit             # hook anti-secretos (activar: git config core.hooksPath .githooks)
├── .streamlit/config.toml     # tema del dashboard (Streamlit)
├── logs/                      # logs de ejecución (ingesta.log)
├── prompt/                    # prompts de IA editables (.md)
│   ├── extractor.md           #   F1: texto → JSON estandarizado
│   ├── evaluador.md           #   F2: perfil + requisitos → evaluación
│   └── chatbot.md             #   F4: narrativa opcional del chat
├── config/
│   ├── tarifas.json           #   tarifas $/1M tokens (regla de negocio)
│   └── vacantes/              #   requisitos por vacante (regla de negocio)
│       ├── ANALISTA_DE_DATOS.json
│       ├── DESARROLLADOR_BACKEND.json
│       └── EJECUTIVO_COMERCIAL.json
├── data/                      # datos de candidatos (NO a git) — flujo local único
│   ├── bronze/                #   originales brutos por <fecha>/<vacante>/
│   ├── silver/candidatos/     #   <sha1(mensaje_id)>.json (idempotente)
│   └── gold/evaluacion/       #   <vacante_id>/<id>.json + ranking.json
├── data_demo/                 # datos ficticios versionados (deploy Vercel)
├── api/index.py               # entry point ASGI para Vercel
├── vercel.json                # build @vercel/python + rutas
├── runtime.txt                # 3.12
├── requirements.txt           # subset mínimo para el build de Vercel
├── .vercelignore              # excluye .env*, data/, logs/, tools/
├── tools/
│   ├── generar_datos_demo.py  # 30+ candidatos ficticios → data_demo/ (o --destino data)
│   └── verificar_secretos.py  # escáner anti-secretos (claves/tokens en el repo)
└── src/agente_rrhh/
    ├── __init__.py
    ├── core/                  # base común a TODAS las fases
    │   ├── __init__.py
    │   ├── config.py          #   .env, estados, parámetros y rutas
    │   ├── logging_setup.py   #   logging consola + archivo (logs/ingesta.log)
    │   ├── sanitizer.py       #   normalización UTF-8, sin tildes, espacios
    │   ├── raw_store.py       #   capa bronze: originales + purga/dedupe
    │   ├── json_store.py      #   capa silver: un JSON por candidato
    │   ├── gold_store.py      #   capa gold: evaluaciones + ranking (atómico)
    │   ├── vacantes.py        #   requisitos por vacante + slug
    │   ├── llm.py             #   fachada única de IA (Gemini/Groq + tokens)
    │   ├── prompts.py         #   carga de prompts .md + parseo JSON tolerante
    │   └── costo.py           #   bitácora jsonl + cálculo de costos estimados
    ├── ingestion/             # FASE 1 — Ingesta y Extracción (Agente 1)
    │   ├── __init__.py
    │   ├── imap_client.py     #   IMAP SSL, filtro asunto/fecha, BODY.PEEK[]
    │   ├── extractor.py       #   texto de PDF/DOCX/TXT/MD + errores
    │   ├── agent_extractor.py #   Gemini: texto → JSON
    │   └── pipeline.py        #   orquestación del lote + reintentos IA
    ├── evaluation/            # FASE 2 — Match Score (Agente 2)
    │   ├── __init__.py
    │   ├── reglas.py          #   pesos 50/30/20, umbrales, clamps
    │   ├── agente_evaluador.py#   Groq: perfil + requisitos → JSON
    │   └── pipeline_evaluacion.py # silver "Listo" → gold + ranking
    ├── dashboard/             # FASE 3 — Dashboard Streamlit
    │   ├── __init__.py
    │   ├── consultas.py       #   lectura gold/silver (sin UI, testeable)
    │   └── app.py             #   UI (Ranking / Postulante / Postulaciones / Metodología)
    └── chatbot/               # FASE 4 — Chatbot de consultas
        ├── __init__.py
        ├── api.py             #   FastAPI + endpoints + SPA
        ├── motor.py           #   motor code-first (clasificador + utilidades)
        ├── sesion.py          #   contexto ligero por sesión + límite IA demo
        ├── datos.py           #   acceso a silver/gold (reutiliza consultas)
        ├── simulador.py       #   re-pesaje del score sin IA
        ├── preguntas_generales.py # FAQ de respaldo (fallback)
        └── frontend/
            ├── index.html     #   SPA vanilla (Chat/Simulador/Brechas/Costos/Fase técnica)
            ├── app.js         #   lógica del cliente (fetch a /api/*)
            └── style.css      #   estilos responsivos
```

> `data/` y `logs/` nunca se versionan (datos personales de candidatos);
> `data_demo/` sí se versiona (datos 100 % ficticios, generados por script) y
> es el único dataset que viaja al deploy Vercel.

---

## 3. FASE 1 — Ingesta y Extracción de Candidaturas (Agente 1)

### 3.1 `core/config.py`
- `@dataclass(frozen=True) Config` con las variables del §7 y propiedades de
  rutas `bronze_dir`, `silver_dir`, `gold_dir`.
- Constantes de estado (§1), `IMAP_HOST="imap.gmail.com"`, `IMAP_PUERTO=993`,
  `EXTENSIONES_PERMITIDAS={".pdf",".docx",".txt",".md"}`, modelos por defecto y
  `CONSULTAS_IA_DEMO_DEFAULT=3`.
- `Config.desde_env()` (carga `.env` con `python-dotenv`) y `Config.validar()`
  que devuelve las variables requeridas ausentes (`EMAIL`, `API_EMAIL`/`PASSWORD`).
- `PASSWORD` es respaldo de `API_EMAIL`.

### 3.2 `core/logging_setup.py`
- `configurar_logging(nivel)` → consola (`sys.stdout`) + archivo
  `logs/ingesta.log` (UTF-8), formato `%(asctime)s | %(levelname)-7s | %(message)s`.

### 3.3 `core/sanitizer.py`
- `quitar_tildes()` (NFKD) y `sanitizar()`: quita caracteres de control,
  normaliza CRLF, normaliza NFKC, colapsa espacios y líneas vacías, quita
  tildes y recorta.

### 3.4 `core/raw_store.py` (capa bronze)
- `nombre_seguro()` (path-safe para Windows).
- `guardar(nombre, contenido, fecha, vacante)` →
  `data/bronze/<fecha>/<vacante>/<archivo>`; si existe copia idéntica devuelve
  la ruta sin duplicar; si difiere, añade sufijo `_<uuid8>`.
- `deduplicar()` elimina copias `_<uuid>` idénticas al original.
- `limpiar_por_dias(dias)` y `limpiar_carpetas_vacias()`.

### 3.5 `core/json_store.py` (capa silver)
- Nombre de archivo `sha1(mensaje_id).json` (función `_hash_mensaje_id`).
- API tipo "base de datos" (reemplaza a MongoDB, misma semántica):
  `verificar_conexion`, `existe_mensaje`, `guardar_candidato` (devuelve False si
  ya existe = idempotencia), `pendientes_reintento`, `actualizar_tras_reintento`,
  `candidatos(estado=None)`, `cerrar()`.
- Escritura **atómica** (archivo temporal + `os.replace`).

### 3.6 `core/llm.py` (fachada única de IA)
- `generar_texto(proveedor, modelo, api_key, prompt, temperature=0.2,
  formato_json=True) -> (texto, uso_tokens)` (`temperature`/`formato_json` son
  keyword-only en la implementación real).
- Proveedores: `gemini` (SDK `google-genai`) y `groq` (SDK `openai` con
  `base_url="https://api.groq.com/openai/v1"`, `response_format=json_object`
  solo si `formato_json`). Cada uno devuelve `uso_tokens` con `prompt`,
  `completado`, `total`.
- Errores se envuelven en `ErrorModelo`; clientes con `lru_cache`.

### 3.7 `core/prompts.py`
- `cargar_prompt(ruta, placeholders)` (valida que cada `{{clave}}` exista) y
  `parsear_json(respuesta)` (tolera bloque ```json, extrae el primer objeto `{…}`).

### 3.8 `core/vacantes.py`
- `slug_vacante(vacante_id)` (mayúsculas, sin tildes, espacios → `_`).
- `RequisitosVacante(dir_base).cargar(vacante_id)` → dict con clave `requisitos`;
  lanza `ErrorRequisitos` si el archivo falta o es inválido.

### 3.9 `core/gold_store.py` (capa gold)
- Guarda `data/gold/evaluacion/<vacante>/<id_candidato>.json` (escritura
  atómica) y **recalcula** `ranking.json` (ordena por `match_score` desc).
- Filas del ranking: `{vacante_id, id_candidato, nombre, email_remitente,
  match_score, clasificacion, fecha_evaluacion}` — SIN teléfono. El generador
  demo `tools/generar_datos_demo.py` agrega el teléfono con una función propia.
- `existe_evaluacion(vacante_id, id_candidato)` para idempotencia.

### 3.10 `core/costo.py`
- Bitácora `data/gold/costo/uso_chat.jsonl` (append simple, `registrar_uso`),
  lectura `leer_usos`, agregado `resumir`, y `calcular_costo` con tarifas
  editables de `config/tarifas.json` ($/1M tokens, `entrada`/`salida`).

### 3.11 `ingestion/imap_client.py`
- `Postulacion` (dataclass) con: `numero`, `mensaje_id`, `asunto`,
  `vacante_id`, `remitente`, `adjuntos[(nombre, bytes)]`, `cuerpo`,
  `remitente_nombre/email/dominio`, `fecha_envio`, `x_mailer`.
- `ImapClient(cfg)`: `conectar()` (SSL `imap.gmail.com:993`,
  `timeout=IMAP_TIMEOUT`, `select("INBOX")`), `listar_postulaciones()`,
  `marcar_leido(numero)`, `cerrar()`.
- Búsqueda en servidor: `UNSEEN`, `SINCE <fecha>` (si `DIAS_ATRAS>0`, fecha =
  hoy − (DIAS_ATRAS − 1)), y `SUBJECT <primera palabra ASCII del prefijo>`
  (con fallback sin SUBJECT). Verificación local de que el asunto comienza con
  `ASUNTO`; `vacante_id = asunto[len(prefijo):].strip()`.
- `BODY.PEEK[]` para **no marcar leídos** al inspeccionar. Si `Message-ID`
  falta, se genera `sin-id|<sha1 de remitente|fecha|vacante|asunto>`.

### 3.12 `ingestion/extractor.py`
- `extraer_adjunto(nombre, contenido)`: PDF (`pdfplumber`), DOCX
  (`python-docx`, párrafos + tablas), TXT/MD (utf-8/latin-1).
- Errores: `ArchivoIlegibleError` (PDF escaneado/corrupto o DOCX dañado/vacío) y
  `FormatoNoPermitidoError` (extensión fuera de las permitidas).
- `formato_origen(nombre)` → extensión en MAYÚSCULAS (`PDF | DOCX | TXT | MD`);
  el valor `CORREO` no sale de esta función: lo asigna el pipeline.

### 3.13 `ingestion/agent_extractor.py`
- `AgenteExtractor(api_key, modelo, prompt_ruta)`: `extraer(texto, dry_run)`
  carga `prompt/extractor.md` con `{{texto_candidato}}` y llama a Gemini vía
  `core.llm`. En `dry_run` devuelve JSON de ejemplo vacío sin gastar cuota.

### 3.14 `ingestion/pipeline.py`
- `PipelineIngesta(cfg, dry_run, max_mensajes)`:
  - 1) reintenta los `Pendiente: Reintento IA` (texto crudo guardado) y
  - 2) procesa los correos nuevos: extracción → sanitización → IA → silver.
- Lógica de adjuntos: prueba todos los adjuntos hasta encontrar uno legible;
  sin adjunto legible usa el cuerpo del correo (`formato_origen="CORREO"`); si
  nada sirve → `Ilegible`.
- Ruta bronze siempre se guarda (adjunto usado o cuerpo como `<vacante>.txt`).
- Documento silver (§3.15); `texto_crudo` se conserva **solo** en estado
  `Pendiente: Reintento IA` (para el reintento) y se borra al tener éxito.
- `--dry-run`: sin IA, sin escrituras en silver, sin marcar leídos (sí guarda
  bronze).
- Resumen del lote con `Counter` por estado + detalle por correo.

### 3.15 Documento del candidato (capa silver)

| Campo | Contenido |
| :--- | :--- |
| `mensaje_id` | Message-ID de Gmail (único; idempotencia). Si falta, hash de respaldo |
| `id_candidato` | `uuid4().hex` (32 hex) |
| `vacante_id` | Puesto extraído del asunto |
| `email_remitente` | From crudo |
| `remitente_metadatos` | `{nombre, email, dominio}` |
| `fecha_envio` / `fecha_ingesta` | Cabecera `Date` / momento de extracción (ISO UTC) |
| `x_mailer` | Cliente de correo (cabecera `X-Mailer`) |
| `ruta_archivo_raw` | Ruta del original en `data/bronze/` |
| `formato_origen` | PDF / DOCX / TXT / MD / CORREO |
| `datos_json` | Salida del Agente 1 |
| `texto_crudo` | Texto saneado conservado (solo reintentos IA) |
| `estado_procesamiento` | Ver matriz de excepciones |
| `motivo` | Descripción del error (o `null`) |
| `fecha_reintento` | Último reintento IA exitoso (el documento inicial NO incluye esta clave; solo se escribe tras un reintento exitoso) |

**Matriz de excepciones F1:**

| Escenario | Acción del sistema | Estado |
| :--- | :--- | :--- |
| El asunto no cumple `ASUNTO` | Se omite el correo | N/A |
| Adjunto corrupto o PDF de imagen | Se interrumpe el flujo a la IA | `Error: Archivo Ilegible` |
| Formato de adjunto no permitido | Se omite la lectura | `Error: Formato No Permitido` |
| Fallo o pérdida de conexión con la API | Se conserva el texto para el siguiente lote | `Pendiente: Reintento IA` |
| Procesamiento exitoso | Extracción + JSON | `Listo para Evaluación` |

### 3.16 `prompt/extractor.md`
Contiene el esquema JSON objetivo (§3.17), reglas de unificación de sinónimos
("Trayectoria"/"Historial Laboral" → `experiencia_laboral`; "Estudios" →
`formacion_academica`), **exclusión deliberada de foto/edad/género/dirección/
estado civil**, uso de `null`/`[]` ante ausencia y "responde SOLO con JSON
válido". Termina con `## Texto del candidato\n\n{{texto_candidato}}`.

### 3.17 JSON resultante del Agente Extractor

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
      { "puesto": "Analista de Datos Junior", "duracion_anos": 1.5,
        "descripcion": "Dashboards y consultas SQL." }
    ],
    "formacion_academica": [
      { "grado": "Egresado", "carrera": "Ingeniería de Sistemas",
        "institucion": "UNMSM" }
    ],
    "certificaciones": ["Power BI Data Analyst"]
  },
  "control_sesgo": {
    "atributos_excluidos": ["foto", "edad", "genero", "direccion", "estado_civil"]
  }
}
```

---

## 4. FASE 2 — Evaluación y Match Score (Agente 2)

### 4.1 `config/vacantes/<SLUG>.json` (regla de negocio)

```json
{
  "vacante": "ANALISTA DE DATOS",
  "requisitos": {
    "habilidades": {
      "esenciales": ["Python", "Microsoft SQL Server", "Power BI", "Excel",
                     "Pensamiento analítico", "Resolución de problemas"],
      "opcionales": ["Oracle", "C++", "Java", "Office", "Inglés",
                     "Trabajo en equipo", "Organizado", "Orientación a resultados",
                     "Adaptabilidad", "Mejora Continua"]
    },
    "experiencia_minima_anos": 0,
    "formacion": {
      "carreras": ["Ingeniería de Sistemas", "Ingeniería de Datos",
                   "Estadística", "Ciencias de la Computación"]
    }
  }
}
```

### 4.2 `evaluation/reglas.py`
- `PESOS = {"habilidades": 0.5, "experiencia": 0.3, "formacion": 0.2}`.
- `UMBRAL_ALTA = 80`, `UMBRAL_MEDIA = 50`.
- `normalizar_score()` (clamp 0–100 entero, tolera `None`/texto),
  `clasificar(score)` (Alta/Media/Baja).
- `componer_puntaje(datos_ia)`:
  - Si la IA entregó los tres parciales en `desglose`, calcula
    `desglose = {bloque: {peso, parcial, puntos}}` con `puntos = parcial*peso`
    redondeado y `match_score = suma(puntos)` (garantiza que los pesos sumen 100).
  - Si no, usa `match_score` de la IA clampeado a 0–100 (y `desglose={}`).

### 4.3 `evaluation/agente_evaluador.py`
- `AgenteEvaluador(api_key, modelo, prompt_ruta).evaluar(perfil, requisitos,
  dry_run=False) -> (datos_ia, uso_tokens)`.
- Carga `prompt/evaluador.md` con `{{requisitos_vacante}}` y
  `{{perfil_candidato}}` (JSON) y llama a Groq vía `core.llm` (proveedor fijo
  `groq` en código; `PROVEEDOR_EVALUADOR` del `.env` no lo altera).
- En `dry_run` devuelve un simulado (desglose 100/0/100, uso 0).

### 4.4 `evaluation/pipeline_evaluacion.py`
- Filtra silver por estado `Listo para Evaluación` (opcional `--vacante`),
  omite ya evaluados (gold) y sin requisitos (aviso en log), evalúa **1 llamada
  por candidato** y guarda el documento gold + ranking.
- Errores de IA/JSON inválido → quedan en silver sin tocar y se marcan en el
  resumen como `Pendiente: Reintento Evaluación`.
- El perfil que se envía a la IA es `{vacante_id, datos_contacto,
  datos_estructurados}`; el contacto **no puntúa**.

### 4.5 Documento de evaluación (capa gold)

| Campo | Contenido |
| :--- | :--- |
| `id_candidato`, `vacante_id`, `mensaje_id` | Identificadores (idempotencia) |
| `nombre_completo`, `telefono`, `email_remitente` | Datos de contacto (no puntúan) |
| `fecha_envio` / `fecha_evaluacion` | Cabecera / momento de la evaluación (ISO) |
| `match_score` | Puntaje 0–100 calculado por `reglas.py` |
| `clasificacion` | `Alta` (≥80), `Media` (≥50), `Baja` (<50) |
| `desglose` | Peso, parcial y puntos por bloque |
| `fortalezas` / `brechas` | Listas que reporta la IA |
| `justificacion` | 2–4 frases del veredicto que reporta la IA |
| `requisito_esencial_ausente` | Alertas de campos obligatorios sin evidencia |
| `requisitos_evaluados` | Snapshot de los requisitos usados |
| `proveedor` / `modelo` / `uso_tokens` | Trazabilidad de la llamada (`proveedor` se escribe fijo `groq`) |
| `estado_procesamiento` | `Evaluado` |

**Matriz de excepciones F2:**

| Escenario | Acción del sistema | Estado |
| :--- | :--- | :--- |
| Sin requisitos para la vacante | Se omite y se avisa en el log | N/A |
| Candidato ya evaluado | Se omite (idempotencia) | `Evaluado` (previo) |
| Fallo de la API o JSON inválido | No se escribe gold; reintenta en el siguiente lote | `Pendiente: Reintento Evaluación` |
| Éxito | Evaluación + ranking | `Evaluado` |

### 4.6 `prompt/evaluador.md`
Exige responder SOLO JSON con el esquema: `desglose` (0–100 por bloque),
`desglose_puntos` (aportes ponderados), `match_score` (entero 0–100), `fortalezas`,
`brechas` (incluye siempre los esenciales ausentes), `requisito_esencial_ausente`
y `justificacion` (2–4 frases). Pide normalizar sinónimos ("SQL Server" ==
"Microsoft SQL Server", "PBI" == "Power BI").

---

## 5. FASE 3 — Dashboard y Visualización (Streamlit)

### 5.1 `dashboard/consultas.py` (capa de lectura, sin UI)
- `estado_amigable()` mapea estados internos a lenguaje RRHH
  (ej. `Listo para Evaluación` → "Pendiente de evaluación").
- `listar_vacantes_con_ranking(gold_dir)`, `ranking_vacante(gold_dir, carpeta)`
  (con `posicion`, recalcula si falta `ranking.json`),
  `detalle_candidato(gold_dir, silver_dir, carpeta, id)` (gold + silver unido,
  con `puntos_por_bloque`), `resumen_ingesta(silver_dir, gold_dir)` (conteos por
  situación y vacante; **"evaluados" se deriva de gold**, no de silver),
  `sugerencia_clasificacion(clasificacion)` (decisión a partir de la
  clasificación: Alta/Media/Baja).

### 5.2 Reglas de negocio del panel
- **Sugerencia RRHH** (estática): **Alta** → "Pase a fase técnica", **Media** →
  "Revisión manual", **Baja** → "No avanza".
- Lecturas cacheadas 30 s + botón "Actualizar información".

### 5.3 `dashboard/app.py` (UI)
Página ancha con CSS propio (badges, tarjetas, chips de habilidades) y 4
pestañas:
- **Ranking**: selector de vacante, métricas (evaluados, alta/media/baja,
  promedio), tabla filtrable con barra de progreso y gráfico de distribución.
- **Postulante**: puntaje, nivel, contacto, sugerencia visual, fortalezas,
  aspectos por reforzar (esenciales ausentes resaltados en rojo), justificación,
  explicación 50/30/20 y resumen de la hoja de vida (silver).
- **Postulaciones**: total, situación por estado, por vacante y aviso de
  pendientes de evaluación.
- **Metodología**: proceso en 4 pasos, fórmula 50/30/20, niveles, sin sesgos y
  significado de cada situación (lenguaje del área de talento).

### 5.4 `.streamlit/config.toml`
Tema con `primaryColor="#2563eb"`, fondo `#f1f5f9`, `secondaryBackgroundColor="#ffffff"`,
`textColor="#0f172a"`, `font="sans serif"` y `[server] runOnSave=true`.

### 5.5 Nota de acceso (MVP)
El dashboard F3 **no pide login** (decisión del MVP: solo el chatbot F4 está
autenticado). Si más adelante se quiere restringir el panel, se agrega un
"gate" en `app.py` (formulario usuario/contraseña en `st.session_state`) que
valide contra las mismas `ADMIN_USUARIO`/`ADMIN_CLAVE` del `.env`.

---

## 6. FASE 4 — Chatbot de consultas de RRHH (FastAPI + SPA)

App web responsiva que escucha **solo en `127.0.0.1`**. Motor **code-first**:
todas las utilidades y bloques visuales se resuelven en código ($0); la IA es
opcional (`PROVEEDOR_CHAT` vacío/`ninguno`/`none`/`offline` = offline).

### 6.1 Módulos
- **`sesion.py`**: contexto ligero por sesión (entidad en foco: vacante/
  candidato) + contador de consultas IA del modo demo. `Sesion` y
  `AlmacenSesiones` (thread-safe, UUID).
- **`datos.py`**: lee gold/silver **reutilizando `dashboard.consultas`**
  (`vacantes`, `ranking`, `detalle`, `resumen_ingesta`; `docs_evaluados` es
  función propia de `datos.py`), `habilidades`, `experiencia_anos`,
  `formaciones`, `dominio`, `tokens_f2`.
- **`motor.py`**: `MotorChat` con `resolver(mensaje, sesion)`. Clasifica la
  intención por reglas (normalización sin tildes) y despacha a manejadores:
  - `saludo`, `ayuda`, `reiniciar`, `ranking`, `candidato`, `fase_tecnica`,
    `pipeline`, `brechas`, `comparar`, `origen`, `borrador`, `costos`,
    `fallback` (con preguntas generales del área).
  - Bloques visuales: `tabla`, `tarjetas`, `lista` (con `clase` alta/media/baja).
  - `_aplicar_ia_opcional()`: si hay proveedor, clave y cuota `sesion.usar_ia()`,
    mejora la narrativa con el LLM (prompt `chatbot.md`) y registra el uso en
    `core.costo`. El proveedor es `PROVEEDOR_CHAT` (`gemini` o `groq`; la clave
    se elige según el proveedor: `GEMINI_API_KEY` o `GROQ_API_KEY`;
    `""`/`ninguno`/`none`/`offline` = modo offline). Si falla o no hay clave,
    responde offline y avisa.
- **`simulador.py`**: re-pesaje del score a partir del `desglose` guardado
  (pesos alternativos normalizados, clamp 0–100, umbrales 80/50, delta vs.
  original). Sin IA.
- **`preguntas_generales.py`**: FAQ en código (qué es el sistema, cómo se
  calcula el score, niveles, costo, privacidad, proveedores, errores,
  requisitos). Se usa en el fallback.
- **`api.py`**: `crear_app(cfg)` → FastAPI con:
  - `/api/health` (público), `/api/login`, `/api/logout`, `/api/me`,
    `/api/config`, `/api/chat`, `/api/vacantes`, `/api/ranking`,
    `/api/brechas`, `/api/simular`, `/api/costos`, `/api/faq`,
    `/api/sesiones/nueva`.
  - Frontend SPA en `frontend/` (`/` sirve `index.html`, `/static` estático).
  - Handler global para devolver 500 sin romper la app.
- **`frontend/app.js` / `index.html` / `style.css`**: SPA vanilla (sin
  dependencias en el navegador) con vistas Chat, Simulador, Brechas, Costos y
  Fase técnica; muestra el límite de IA restante y el botón "Nuevo chat". La
  vista Fase técnica lee el teléfono de las filas del ranking (en el flujo local
  real esas filas no incluyen teléfono; solo la demo lo agrega — ver §3.9).

### 6.4 Login del asistente (control de acceso)
- `Config` lee `admin_usuario`/`admin_clave` de `ADMIN_USUARIO`/`ADMIN_CLAVE`;
  `login_habilitado = ambas no vacías`. Credenciales deshabilitadas → login
  desactivado con aviso en consola y en la UI (acceso abierto para pruebas).
- `POST /api/login` verifica con `hmac.compare_digest` y emite
  `token = secrets.token_urlsafe(32)` (válido 12 h, guardado en memoria del
  proceso). `POST /api/logout` lo invalida; `GET /api/me` valida la sesión.
- Todos los `/api/*` exigen `Authorization: Bearer <token>` excepto
  `/api/health`, `/api/login`, `/api/logout` y `/api/me` (401 sin token).
- La SPA guarda el token en `localStorage` (`rrhh_token`), muestra una vista
  de login a pantalla completa (usuario/contraseña) y regresa a ella ante un
  401. Botón "Salir" en el sidebar. Nunca loguear credenciales.

### 6.2 `prompt/chatbot.md`
Prompt de narrativa opcional: no inventar datos (solo usar `{{contexto_datos}}`),
respetar la entidad en foco (`{{entidad_en_foco}}`), responder solo a
`{{pregunta}}`, y mencionar que los bloques visuales los genera el código.

### 6.3 Modo demo (MVP Vercel)
- `DEMO_CONSULTAS_IA` (default `3`) limita las consultas con IA **por
  conversación**; al agotarse, el motor code-first sigue respondiendo con datos
  verificados (0 tokens). Contador visible en la SPA; se reinicia con
  "Nuevo chat".

---

## 7. Deploy MVP en Vercel (modo demo del chatbot F4)

- **`api/index.py`**: entry point ASGI expone `app = crear_app()` y usa
  `DATA_DIR=data_demo` (`os.environ.setdefault`). Agrega la raíz a `sys.path`.
- **`vercel.json`**: `@vercel/python` sobre `api/index.py` + ruta `/(.*)`.
- **`runtime.txt`**: `3.12`.
- **`requirements.txt`**: subset mínimo (`fastapi`, `uvicorn`,
  `python-dotenv`, `openai`).
- **`.vercelignore`**: excluye `.env`, `.env.*`, `data/`, `logs/`,
  `.venv/`, `*.pdf`, `*.log`, `tools/`.
- **`tools/generar_datos_demo.py`**: genera `data_demo/` con **30+ candidatos
  ficticios** (2–3 vacantes, silver + gold + ranking), versionable. Con
  `--destino data` re-siembra el flujo local (escribe/fusiona, no borra).
- **`.env.example`**: plantilla completa del §8, con placeholders y sin
  secretos.
- **Env Vars en Vercel**: `ADMIN_USUARIO`/`ADMIN_CLAVE` para el login del MVP
  (nunca dentro del repo). **Dejar `PROVEEDOR_CHAT` sin definir** en Vercel:
  el MVP corre offline ($0); `gemini`/`groq` solo en el `.env` local.
- **`config/tarifas.json`**: `{moneda, unidad, nota, tarifas}` con entradas por
  modelo y clave `defecto` ($/1M tokens, `entrada`/`salida`; Gemini en 0).

---

## 8. Variables del `.env` (todas configurables)

```dotenv
# 1) Cuenta de correo y acceso IMAP
EMAIL=tu_correo@gmail.com
API_EMAIL=xxxx xxxx xxxx xxxx    # App Password IMAP (16 caracteres)
# PASSWORD=                      # opcional: respaldo de API_EMAIL
IMAP_TIMEOUT=30

# 1b) Asunto, ventana de búsqueda y agenda
ASUNTO=POSTULACION -
DIAS_ATRAS=1                     # 1 = hoy; 0 = sin límite de fecha
HORA_INGESTA=18:00               # hora del lote programado (--programar)

# 2) Gemini (Agente Extractor, F1)
GEMINI_API_KEY=tu_clave_AiZa...  # requerida
MODELO_GEMINI=gemini-3.5-flash
PROMPT_EXTRACTOR=prompt/extractor.md

# 3) Evaluación (F2 — Groq)
GROQ_API_KEY=tu_clave_groq
# PROVEEDOR_EVALUADOR se lee del .env pero el proveedor efectivo es SIEMPRE groq
PROVEEDOR_EVALUADOR=groq
MODELO_EVALUADOR=openai/gpt-oss-120b
PROMPT_EVALUADOR=prompt/evaluador.md

# 4) Chatbot (F4 — IA opcional; vacío/ninguno/none/offline = offline, $0)
PROVEEDOR_CHAT=                   # gemini | groq | (vacío/ninguno/none/offline = offline, $0)
MODELO_CHAT=openai/gpt-oss-120b   # openai/gpt-oss-120b (groq) o gemini-3.5-flash (gemini)
DEMO_CONSULTAS_IA=3

# 4b) Acceso al chatbot F4 (login; vacías = login desactivado)
ADMIN_USUARIO=                   # usuario del login (solo tú lo sabes)
ADMIN_CLAVE=                     # contraseña del login (solo tú la sabes)

# 5) Persistencia y regla de negocio
DATA_DIR=data
RAWDATA_RETENCION_DIAS=90
RUTA_VACANTES=config/vacantes
RUTA_TARIFAS=config/tarifas.json
```

> `data/` es el flujo local único por defecto. Para probar el modo demo
> (ficticio): `set DATA_DIR=data_demo` antes de lanzar `main.py chat`.
> `data_demo/` se regenera con `tools/generar_datos_demo.py`.
>
> Resguardo: si una key Gemini responde `403 PERMISSION_DENIED` (bloqueo a
> nivel de **proyecto** de Google Cloud, no de key), usa `PROVEEDOR_CHAT=groq`
> para el chat local; `gemini` queda disponible al crear la key en un proyecto
> habilitado (Generative Language API).

---

## 9. CLI de `main.py` (punto de entrada único)

```bash
uv run python main.py                          # F1: lote real (IMAP + Gemini + silver)
uv run python main.py --dry-run                # F1: sin gastar cuota ni guardar silver
uv run python main.py --max 5                  # F1: máximo 5 correos
uv run python main.py --programar              # F1: lote diario a HORA_INGESTA (loop)
uv run python main.py limpiar [--dias 7]       # F1: purga bronze (retención .env)
uv run python main.py evaluar [--vacante X] [--dry-run]   # F2
uv run python main.py dashboard [--port 8501]  # F3: panel Streamlit (solo red local)
uv run python main.py chat [--port 8510]       # F4: app web (solo localhost)
```

- `--dry-run`: extrae y sanitiza, **no llama a la IA ni escribe silver/gold**,
  no marca correos leídos. Sí deja la copia en bronze.
- `--verbose`: logs en DEBUG.
- `dashboard` y `chat` deben recomendar ejecutarse **solo en red local**
  (muestran datos personales).
- `--port`: default único `8501` para `dashboard` **y** `chat`; el `8510` de
  los ejemplos es solo una sugerencia (usar `--port 8510` para el chat).
- `chat` pide inicio de sesión si `ADMIN_USUARIO`/`ADMIN_CLAVE` están
  configurados en `.env`; con ambas vacías funciona sin login (aviso visible).

---

## 10. Dependencias (`pyproject.toml`)

```toml
[project]
name = "agente-rrhh"
version = "0.1.0"
description = "Agente de RRHH - Fase 1: ingesta y extraccion de candidaturas desde Gmail via IMAP, estandarizacion JSON con Gemini y persistencia local (medallion bronze/silver/gold)."
# Nota: la description real del pyproject quedó en texto de solo-F1; aquí se
# reproduce tal cual (alineado al código actual).
readme = "README.md"
requires-python = ">=3.12"
dependencies = [
    "fastapi>=0.141.1",
    "google-genai>=2.22.0",
    "openai>=1.40",
    "pdfplumber>=0.11.10",
    "python-docx>=1.2.0",
    "python-dotenv>=1.2.3",
    "schedule>=1.2.2",
    "streamlit>=1.63.0",
    "uvicorn>=0.52.4",
]
```

`imaplib` es de la librería estándar (no se instala). `.python-version` = `3.12`.

---

## 11. `.gitignore` y `.env.example`

- `.gitignore` debe ignorar como mínimo: `.env`, `.env.*` (con excepción de
  `!.env.example`), `data/`, `logs/`, `__pycache__/`, `*.py[oc]`,
  `.venv/`, caches de test (`*.pytest_cache`, `*.mypy_cache`, `*.ruff_cache`),
  `.coverage`, `htmlcov/`, `.vscode/`, `.idea/`, archivos SO/editor y temporales.
- `.env.example`: copia del §8 con secciones comentadas explicando cada
  variable (sin valores reales).

---

## 12. Orden de implementación (checkpoints)

1. **Esqueleto y convenciones**: `pyproject.toml`, `.python-version`,
   `.gitignore`, `.env.example`, `.githooks/pre-commit` +
   `tools/verificar_secretos.py` (guard anti-secretos), estructura de carpetas y
   `src/agente_rrhh/{core,ingestion,evaluation,dashboard,chatbot}/__init__.py`.
2. **`core/` completo** (config → logging → sanitizer → raw_store →
   json_store → vacantes → llm → prompts → gold_store → costo).
3. **F1** (`imap_client` → `extractor` → `agent_extractor` → `pipeline`) +
   `prompt/extractor.md` + `main.py` (comandos base, `--dry-run`, `limpiar`,
   `--programar`). *Verificar*: `compileall` + `--dry-run`.
4. **F2** (`reglas` → `agente_evaluador` → `pipeline_evaluacion`) +
   `config/vacantes/*.json` + `prompt/evaluador.md` + comando `evaluar`.
5. **F3** (`consultas` → `app` + `.streamlit/config.toml`) + comando `dashboard`.
6. **F4** (sesion → datos → simulador → preguntas_generales → motor → api →
   frontend) + `prompt/chatbot.md` + comando `chat`.
7. **Datos de prueba y demo** (`tools/generar_datos_demo.py` → `data_demo/`
   versionable para Vercel; con `--destino data` re-siembra el flujo local).
8. **Deploy Vercel** (`api/index.py`, `vercel.json`, `runtime.txt`,
   `requirements.txt`, `.vercelignore`, `config/tarifas.json`).
9. **Documentación**: `README.md` (visión, fases, arquitectura, especificación
   por fase, configuración, uso, deploy y seguridad), `PENDIENTES.md` (bitácora
   Scrum: F1–F4 hechos + backlog), `AGENTS.md` (convenciones y estructura),
   `DOCUMENTACION.md` (detalle opcional).

---

## 13. Definición de listo (verificación final)

- [ ] `uv run python -m compileall -q src main.py` termina sin errores.
- [ ] `uv run python main.py --dry-run` no llama a la IA y no escribe silver.
- [ ] `uv run python main.py limpiar` purga bronze según retención.
- [ ] F2 calcula el score en código: pesos 50/30/20, umbrales 80/50, clamps 0–100.
- [ ] Sin `GEMINI_API_KEY`/`GROQ_API_KEY` el sistema degrada con aviso (reintentos),
      nunca lanza excepciones no controladas.
- [ ] Dashboard F3 arranca con `main.py dashboard` y responde `/_stcore/health`,
      con lenguaje del área de talento (sin términos silver/gold/tokens en la UI).
- [ ] Chat F4 arranca con `main.py chat`, `/api/health` responde `ok`, y en modo
      offline gasta **0 tokens** (costo $0).
- [ ] Un candidato procesado dos veces no se duplica (idempotencia F1 y F2).
- [ ] El deploy Vercel (modo demo) usa `data_demo/` y excluye `data/`, `logs/`
      y `.env*`.
- [ ] Chat F4 con `ADMIN_USUARIO`/`ADMIN_CLAVE` cargadas: los `/api/*` sin token
      devuelven 401; `/api/login` correcto devuelve token y el endpoint protegido
      responde 200; `/api/logout` invalida la sesión. Con credenciales vacías el
      login queda desactivado con aviso (no bloquea las pruebas).
- [ ] Guard anti-secretos: `uv run python tools/verificar_secretos.py` responde
      `[OK]` con 0 hallazgos; el hook `.githooks/pre-commit` bloquea (exit 1) un
      archivo en stage con una key falsa (`gsk_`/`AIza`/`AQ.Ab`) y aprueba uno
      limpio.

---

## 14. Puesta en marcha en otro dispositivo (replicar, probar y desplegar)

Para reconstruir este sistema con IA en otra máquina y dejarlo **funcional**,
además de regenerar el código, hay que ponerlo operativo. Ejecutar en orden:

1. **Preparar el entorno**: asegurar Python 3.12 + `uv`; instalar con
   `uv sync` y validar con `uv run python -m compileall -q src main.py`.
2. **Credenciales**: copiar `.env.example` → `.env` y completar `EMAIL`/
   `API_EMAIL` (App Password), `GEMINI_API_KEY`, `GROQ_API_KEY` y, si se quiere
   proteger el chatbot, `ADMIN_USUARIO`/`ADMIN_CLAVE`. Nunca generar ni
   versionar estos valores.
3. **Datos de prueba o demo**: el flujo local usa `data/` por defecto. Para el
   modo demo inmediato (ficticio): ejecutar `tools/generar_datos_demo.py`
   (`data_demo/`) y probar con `DATA_DIR=data_demo`. Para sembrar candidatos
   ficticios adicionales en el flujo local: `tools/generar_datos_demo.py
   --destino data` (escribe/fusiona, no borra lo real).
4. **Probar cada fase local**:
   - `uv run python main.py --dry-run` (F1 sin cuota ni silver).
   - `uv run python main.py evaluar --dry-run` (F2 simulada).
   - `uv run python main.py dashboard` (F3, sin login).
   - `uv run python main.py chat --port 8510` (F4):
     `/api/health` responde, la SPA pide login si hay credenciales, los
     `/api/*` responden 401 sin token y 200 con token válido. Si se activó
     IA (`PROVEEDOR_CHAT`) y el proveedor responde `403 PERMISSION_DENIED`,
     cambiar de proveedor (p. ej. `groq`) — ver resguardo del §8.
   - `uv run python main.py limpiar` (purga de bronze).
5. **Deploy Vercel (modo demo)**: el repo se construye solo con `vercel.json`/
   `runtime.txt`/`requirements.txt`; configurar como Env Vars unicamente
   `ADMIN_USUARIO`/`ADMIN_CLAVE` y opcionalmente `DEMO_CONSULTAS_IA`. **Dejar
   `PROVEEDOR_CHAT` sin definir**: el MVP corre offline ($0). El deploy lee
   `data_demo/` (ficticio).
6. **Privacidad**: `data/`, `logs/` y `.env*` jamás salen del equipo; en la
   nube solo viajan las variables de entorno y datos ficticios.

---

*Este prompt es la plantilla maestra. Si ya existe un repo con estos archivos,
la orden es reconstruirlos en limpio (misma especificación, sin archivos
basura); si la carpeta está vacía, créalos desde cero. En ambos casos, respeta
los no negociables del §1 y no generes nada que no esté especificado.*