@echo off
setlocal
REM ============================================================
REM  FLUJO_COMPLETO.bat - TODO en un clic (F1+F2+F3+F4)
REM  Corre el sistema completo de una vez, con pausas entre
REM  fases. Si no hay entorno, ejecuta INSTALAR.bat (uv primero,
REM  fallback pip). Usa .venv si existe; si no, uv run python.
REM  Sirve desde cualquier letra de USB (no fija rutas).
REM ============================================================
cd /d "%~dp0"

echo.
echo  ==========================================
echo    AGENTE RRHH - Flujo completo (F1-F2-F3-F4)
echo  ==========================================
echo.

REM ---- 1) Entorno (instala si hace falta) --------------------
call "%~dp0_entorno.bat"
if errorlevel 1 (
    echo   No hay entorno instalado. Ejecutando INSTALAR.bat...
    call "%~dp0INSTALAR.bat"
    call "%~dp0_entorno.bat"
    if errorlevel 1 (
        echo  [ERROR] No se pudo preparar el entorno. Revisa INSTALAR.bat.
        goto :fin
    )
)
echo   Entorno listo: %RUN_CMD%
echo.

REM ---- 2) .env: si NO existe, crear desde plantilla -----------
if not exist ".env" (
    if exist ".env.example" (
        echo   [AVISO] No hay .env en esta carpeta.
        echo   Creando uno desde .env.example...
        copy /Y ".env.example" ".env" >NUL
        echo   Luego completa tus claves en el archivo .env
        echo   EMAIL, API_EMAIL, GEMINI_API_KEY, GROQ_API_KEY...
    )
)

REM ---- 3) F1 - INGESTA ---------------------------------------
echo.
echo  ==========================================
echo   F1 - INGESTA (IMAP -^> bronze/silver)
echo  ==========================================
%RUN_CMD% main.py
if errorlevel 1 echo   [AVISO] F1 termino con errores. Revisa logs\ingesta.log.
echo.
echo   Revisa data\bronze y data\silver\candidatos.
pause

REM ---- 4) F2 - EVALUAR ----------------------------------------
echo.
echo  ==========================================
echo   F2 - EVALUAR (silver -^> gold, Match Score)
echo  ==========================================
%RUN_CMD% main.py evaluar
if errorlevel 1 echo   [AVISO] F2 termino con errores. Revisa logs\evaluacion.log.
echo.
echo   Revisa data\gold\evaluacion\ y el ranking.
pause

REM ---- 5) F3 - DASHBOARD --------------------------------------
echo.
echo  ==========================================
echo   F3 - DASHBOARD (panel Streamlit F3)
echo   Se abrira el navegador. Ctrl+C para cerrar.
echo  ==========================================
start "" http://localhost:8501
%RUN_CMD% main.py dashboard --port 8501
pause

REM ---- 6) F4 - CHAT -------------------------------------------
echo.
echo  ==========================================
echo   F4 - CHATBOT (asistente web F4)
echo   Se abrira el navegador. Ctrl+C para cerrar.
echo  ==========================================
start "" http://127.0.0.1:8510
%RUN_CMD% main.py chat --port 8510
pause

:fin
echo.
echo  ==========================================
echo   Flujo completado (F1-F2-F3-F4).
echo   Repasa el paso a paso en COMO_EJECUTAR.txt
echo  ==========================================
pause
