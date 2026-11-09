@echo off
setlocal
REM ============================================================
REM  DASHBOARD.bat - Fase 3: panel Streamlit (F3)
REM  Abre el navegador y lanza el dashboard en localhost:8501.
REM  Solo red local (muestra datos personales). Ctrl+C al salir.
REM  Usa .venv si existe; si no, uv run python.
REM ============================================================
cd /d "%~dp0"
call "%~dp0_entorno.bat"
if errorlevel 1 (
    echo.
    pause
    exit /b 1
)
start "" http://localhost:8501
%RUN_CMD% main.py dashboard --port 8501
pause
