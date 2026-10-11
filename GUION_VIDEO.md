# Guion del video demostrativo (A7)

Duración objetivo: **3 a 5 minutos**. Muestra el flujo **F1 -> F2 -> F3 -> F4**
y la **URL en linea** del MVP en Vercel.

- URL publica: https://agente-rrhh-five.vercel.app/
- Repo GitHub: _(completar con el enlace del repositorio)_

> Antes de grabar: verifica la URL en incognito, cierra notificaciones y
> **nunca muestres el `.env` ni claves de API**.

---

## Preparacion (fuera de camara)

1. Terminal abierta en la raiz del proyecto.
2. Navegador con 2 pestanas: la URL de Vercel y `about:blank`.
3. Ten a mano `diagrama_arquitectura_agente_rrhh.png`.
4. Confirma que responde: `https://agente-rrhh-five.vercel.app/`.
5. Herramienta de grabacion: `Win + G` (Xbox Game Bar) u OBS Studio.

---

## Guion con tiempos

### 0:00 – 0:30 | Intro (camara o voz sobre pantalla)

> "Hola, somos el equipo 7. Este es el Agente RRHH: un sistema
> multiagente que automatiza la preseleccion de talento a partir de las
> postulaciones que llegan por correo, con costo operativo cero. Lo
> mostramos de punta a punta: ingesta, evaluacion, dashboard y chatbot."

### 0:30 – 1:00 | Arquitectura

- Muestra `diagrama_arquitectura_agente_rrhh.png`.
- Narra el flujo: **Candidato -> Gmail (IMAP) -> Agente 1 (Gemini) ->
  bronze/silver -> Agente 2 (Groq + reglas 50/30/20) -> gold/ranking ->
  F3 (Streamlit) y F4 (chatbot en Vercel)**.

### 1:00 – 1:30 | URL en linea (requisito eliminatorio)

- Abre `https://agente-rrhh-five.vercel.app/`
- Inicia sesion si el chatbot lo pide.
- Muestra rapido una consulta y el ranking desde el navegador.
- Menciona: "El MVP esta desplegado y es demostrable en linea."

### 1:30 – 2:15 | FASE 1 - Ingesta y extraccion (Agente 1)

Comando:

```bash
uv run python main.py --dry-run
```

- Explica: se conecta a Gmail por IMAP, filtra por asunto y fecha, extrae
  el texto del CV y lo estandariza con Gemini a JSON.
- Muestra las carpetas resultantes: `data/bronze/` y
  `data/silver/candidatos/`.
- Aclara que `--dry-run` no gasta cuota ni marca correos como leidos.

### 2:15 – 3:00 | FASE 2 - Evaluacion y Match Score (Agente 2)

Comando:

```bash
uv run python main.py evaluar --re-evaluar
```

- Explica: 1 llamada de IA por candidato (Groq), y el puntaje 50/30/20 se
  calcula en codigo (`reglas.py`), no se confia en el score del modelo.
- Muestra `data/gold/evaluacion/<VACANTE>/` y `ranking.json` ordenado.

### 3:00 – 3:45 | FASE 3 - Dashboard (Streamlit)

Comando:

```bash
uv run python main.py dashboard
```

- Abre `http://localhost:8501`.
- Muestra: Ranking de postulantes, ficha del postulante (puntaje, nivel,
  fortalezas, brechas) y la pestana Metodologia.
- Resalta la **sugerencia RRHH** por clasificacion (Alta/Media/Baja).

### 3:45 – 4:30 | FASE 4 - Chatbot de consultas

Comando (o usa `demo` para levantar F3+F4 juntas):

```bash
uv run python main.py chat
```

- Abre `http://127.0.0.1:8510`.
- Haz una consulta en lenguaje natural (ej. "ranking de ANALISTA DE DATOS").
- Muestra el **simulador de pesos** y la vista de **Costos** (modo offline = $0).

### 4:30 – 5:00 | Cierre

- Repite la URL: `https://agente-rrhh-five.vercel.app/`
- Menciona el repo de GitHub y que el codigo es verificable.

---

## Version corta: levantar todo de una sola vez

Si quieres grabar F3+F4 juntas y con datos ficticios listos:

```bash
uv run python main.py demo --sin-navegador
```

---

## Checklist antes de subir

- [ ] Duracion entre 3 y 5 minutos.
- [ ] Se ve el flujo F1 -> F2 -> F3 -> F4.
- [ ] Se ve la URL publica de Vercel en funcionamiento.
- [ ] No aparece ninguna clave, token ni el archivo `.env`.
- [ ] Audio claro y pantalla legible (1080p).

---

## Subida y registro

1. Sube el video a **YouTube (no listado)** o **Google Drive** (enlace publico).
2. Copia el enlace en el campo **A7** del
   `Cuestionario_de_Evaluación_RESPUESTAS.docx`.
3. Guarda 2-3 capturas de la app en linea para **G7 / I4 / E9**.
4. Anota el enlace del video aqui: **VIDEO_DEMO = _ (completar)_**
