# Entrega del proyecto en una laptop

Esta carpeta se entrega **lista para usar**. No hace falta saber de Python.

---

## 1. Cómo se abre (un solo paso)

| Sistema | Qué hacer |
| --- | --- |
| **Windows** | Doble clic en **`INICIAR.bat`** |
| **macOS / Linux** | Doble clic en **`iniciar.sh`** (si el sistema lo bloquea: botón derecho → *Abrir*) |

La primera vez tarda **1 a 3 minutos** (descarga Python si falta, crea el
entorno e instala las librerías). Las siguientes, **menos de 10 segundos**.

> **Al copiar la carpeta a otro equipo, no copies `.venv/`** (458 MB y además
> guarda rutas absolutas de esta máquina). El lanzador lo detecta y lo rehace
> solo, pero tardas 1-3 minutos más. Lo que sí conviene copiar es todo lo demás,
> `data/` incluida (trae 30 evaluaciones ya listas para mostrar).

Al terminar se abre el navegador con el sistema listo:

| Interfaz | URL | Qué muestra |
| --- | --- | --- |
| **Chatbot F4** | `http://127.0.0.1:8510` | Consultas en lenguaje natural, ranking, brechas, costos, simulador de pesos y fase técnica |
| **Dashboard F3** | `http://127.0.0.1:8501` | Tabla de candidatos por vacante con *match score* y clasificación |

Para detener todo: cerrar la ventana negra (o `Ctrl+C`).

> Las URLs solo funcionan en ese computador: el sistema está pensado para
> red local porque maneja datos personales de postulantes.

---

## 2. Qué se ve al arrancar

La consola imprime el estado de cada fase antes de abrir el navegador:

```
  ESTADO DEL SISTEMA
  ------------------------------------------------------
  [AVISO] F1 Ingesta (IMAP + Gemini)   Falta EMAIL, API_EMAIL/PASSWORD en .env
  [AVISO] F2 Evaluación (Groq)         Sin GROQ_API_KEY: 31 candidato(s) esperando
  [OK  ] F3 Dashboard (Streamlit)      30 evaluación(es) cargadas desde data/gold
  [OK  ] F4 Chatbot (web)              100 % en código, costo $0
```

- **F3 y F4 funcionan siempre**: se siembran 30+ candidatos **ficticios** en
  `data/` (copia de `data_demo/`), que son los mismos que usa la versión en
  internet. La demo **no cuesta nada**: el chatbot responde 100 % en código.
- **F1 y F2 con IA real** necesitan las claves del responsable (sección 3).

---

## 3. Para que F1 y F2 usen IA real (opcional, lo hace el responsable)

Antes de entregar la carpeta, el responsable de RRHH copia su archivo `.env`
real dentro de esta carpeta. Sin ese archivo las dos fases siguen siendo
visibles, pero solo en modo simulado.

```bash
# Linux/macOS
cp /ruta/de/tu/.env .

# Windows (PowerShell)
Copy-Item C:\ruta\de\tu\.env .
```

Claves que habilitan cada fase (referencia completa en `.env.example`):

| Fase | Variables | Sin ellas |
| --- | --- | --- |
| **F1** Ingesta IMAP | `EMAIL`, `API_EMAIL`, `GEMINI_API_KEY` | La ingesta no se puede ejecutar |
| **F2** Match Score | `GROQ_API_KEY` | Solo se puede simular (`--dry-run`) |
| **F4** Narrativa del chat | `PROVEEDOR_CHAT=groq` + `GROQ_API_KEY` | Responde en código, costo $0 |

Con las claves cargadas, la F2 se puede mostrar **en vivo** sobre los candidatos
de prueba (no toca correos reales):

```bash
# Linux/macOS
.venv/bin/python main.py evaluar --vacante "ANALISTA DE DATOS" --re-evaluar

# Windows
.venv\Scripts\python.exe main.py evaluar --vacante "ANALISTA DE DATOS" --re-evaluar
```

> `--re-evaluar` es necesario porque los candidatos de prueba ya vienen
> evaluados: sin ese flag la F2 los omite para no gastar cuota. Con él se
> recalculan los 10 puntajes y el ranking de esa vacante.
>
> El *free tier* de Groq limita el ritmo de llamadas (responde 429 y reintenta
> solo): la vacante completa tarda unos 2 minutos.

> **Seguridad.** `.env` contiene credenciales reales (acceso IMAP y claves de
> IA). No se sube a Git, no se envía por correo ni se versiona. Al terminar la
> entrega: **borrar `.env` y rotar las claves** si el equipo queda fuera de tu
> control. El chequeo anti-secretos (`tools/verificar_secretos.py`) bloquea
> cualquier commit que las incluya por error.

---

## 4. Si algo falla

| Síntoma | Solución |
| --- | --- |
| "No se encontro Python 3.12 o superior" | Instalar Python 3.12 de [python.org](https://www.python.org/downloads/) marcando **"Add python.exe to PATH"** y volver a hacer doble clic |
| Faltan librerías / error de importación | Borrar la carpeta `.venv` y ejecutar `INICIAR.bat` de nuevo (el lanzador ya lo hace solo) |
| El puerto 8501 o 8510 está ocupado | El sistema busca el siguiente libre automáticamente; la URL correcta se imprime en la consola |
| "Entorno virtual no es válido" | Normal si la carpeta se copió desde otro equipo: se rehace solo (1-3 min) |
| "Login desactivado" en el chatbot | Normal: el login solo se activa con `ADMIN_USUARIO` y `ADMIN_CLAVE` en `.env` |
| Sin internet en la primera ejecución | La instalación de librerías requiere conexión una vez |

Detalle de cada fase: `README.md` (secciones 7 y 10) y `PENDIENTES.md`.
