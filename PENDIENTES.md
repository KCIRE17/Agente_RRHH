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

## FASE 2 — Evaluación y Match Score (Agente 2) 🟡 No iniciada

Carpeta `src/agente_rrhh/evaluation/` (esqueleto).

### Por desarrollar

- [ ] 🔴 **Ponderación fija 50/30/20**: Habilidades (50 %), Experiencia
  (30 %), Formación académica (20 %).
  *Aceptación: el puntaje se compone con estos pesos y suma 100 %.*
- [ ] 🔴 **Match Score 0–100** y clasificación: **Alta (80–100)**, **Media
  (50–79)**, **Baja (< 50)**.
  *Aceptación: caso manual conocido da el mismo ranking que el sistema.*
- [ ] 🔴 **Diccionario de habilidades por nivel negocio** (regla de negocio):
  herramienta → nivel (SQL avanzado, básico...) y qué representa para la
  empresa.
- [ ] 🟡 **Fortalezas y brechas**: reporte de requisitos cumplidos y de campo
  obligatorio ausente (puntaje 0 + descripción de alerta).
- [ ] 🟡 **Mitigación de sesgos**: verificar que el cálculo ignora foto/edad/
  género/dirección/estado civil.
- [ ] 🟡 **Modelo de IA**: definir e integrar un modelo compatible para el
  Agente 2 (razonamiento sobre el `datos_json` de F1).
- [ ] 🟡 **Límite de candidatos filtrados** por vacante (regla de negocio).
- [ ] 🟡 **Comando CLI**: `uv run python main.py evaluar [--vacante X]`.
  *Aceptación: escribe `match_score`, `clasificacion`, fortalezas y brechas
  en el JSON del candidato (capa gold).*

### Definición de listo F2

- [ ] Todos los candidatos `Listo para Evaluación` de una vacante tienen
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
| — | F2 Match Score funcionando | ⏳ |
| — | F3 Dashboard Streamlit | ⏳ |
| — | F4 Chatbot | ⏳ |